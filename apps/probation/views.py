import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from employee_onboarding.models import SyncedEmployee
from .models import ProbationChecklist, ChecklistAssignment, ChecklistResponse, AIReport, FinalProbationReport
from .services import notify_employee_via_bitrix24, run_gemini_analysis, run_final_probation_analysis

# Helper to check if current user is Admin or HR
def is_admin_or_hr(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'role', '') in ['ADMIN', 'HR'])

# Public Checklist Submission view (No Auth required, accessible via UUID/ID from Bitrix24 notification)
@csrf_exempt
def submit_checklist(request, assignment_id):
    assignment = get_object_or_404(ChecklistAssignment, id=assignment_id)
    if assignment.status != 'Pending':
        return render(request, 'probation/submit_success.html', {
            'message': 'This checklist has already been submitted. Thank you!',
            'employee': assignment.employee
        })

    checklist = assignment.checklist

    if request.method == 'POST':
        answers = {}
        for q in checklist.questions:
            q_id = q.get('id')
            answers[q_id] = request.POST.get(q_id, '')

        # Save response
        response_obj = ChecklistResponse.objects.create(
            assignment=assignment,
            answers=answers
        )
        
        # Update assignment status
        assignment.status = 'Submitted'
        assignment.submitted_at = timezone.now()
        assignment.save()

        # Trigger Gemini AI analysis
        ai_report = run_gemini_analysis(assignment)
        if ai_report:
            logger_msg = "Gemini analysis successfully completed."
        else:
            logger_msg = "Gemini analysis failed to complete, will retry later."

        return render(request, 'probation/submit_success.html', {
            'message': 'Your checklist response has been successfully submitted and saved. Thank you!',
            'employee': assignment.employee
        })

    return render(request, 'probation/submit_form.html', {
        'checklist': checklist,
        'assignment': assignment,
        'employee': assignment.employee
    })


# API Viewsets for Admin dashboard
class ProbationChecklistViewSet(viewsets.ModelViewSet):
    queryset = ProbationChecklist.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        # We can construct simple serializers on the fly
        from rest_framework import serializers
        class ChecklistSerializer(serializers.ModelSerializer):
            class Meta:
                model = ProbationChecklist
                fields = '__all__'
        return ChecklistSerializer

    def create(self, request, *args, **kwargs):
        if not is_admin_or_hr(request.user):
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class ChecklistAssignmentViewSet(viewsets.ModelViewSet):
    queryset = ChecklistAssignment.objects.all().order_by('-assigned_at')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        from rest_framework import serializers
        class AssignmentSerializer(serializers.ModelSerializer):
            checklist_title = serializers.CharField(source='checklist.title', read_only=True)
            employee_name = serializers.SerializerMethodField()
            scores = serializers.SerializerMethodField()
            trend = serializers.SerializerMethodField()

            class Meta:
                model = ChecklistAssignment
                fields = '__all__'

            def get_employee_name(self, obj):
                return f"{obj.employee.first_name} {obj.employee.last_name or ''}".strip()

            def get_scores(self, obj):
                if hasattr(obj, 'ai_report'):
                    return obj.ai_report.scores
                return None

            def get_trend(self, obj):
                if hasattr(obj, 'ai_report'):
                    return obj.ai_report.trend
                return None

        return AssignmentSerializer

    def create(self, request, *args, **kwargs):
        if not is_admin_or_hr(request.user):
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)
        
        # Avoid direct init issues, call standard perform_create
        response = super().create(request, *args, **kwargs)
        
        # Trigger Bitrix notification for the new assignment
        try:
            assignment_id = response.data.get('id')
            if assignment_id:
                assignment = ChecklistAssignment.objects.get(id=assignment_id)
                notify_employee_via_bitrix24(assignment)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error sending assignment webhook notification: {e}")

        return response


class ProbationDashboardAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not is_admin_or_hr(request.user):
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        total_employees = SyncedEmployee.objects.filter(status='Active').count()
        pending_forms = ChecklistAssignment.objects.filter(status='Pending').count()
        
        today = timezone.localtime(timezone.now()).date()
        submitted_today = ChecklistAssignment.objects.filter(
            status__in=['Submitted', 'Analyzed'],
            submitted_at__date=today
        ).count()

        ai_reports_count = AIReport.objects.count()

        # Calculate Average score
        all_reports = AIReport.objects.all()
        avg_score = 0
        improving_count = 0
        declining_count = 0
        ready_for_confirmation = 0

        if all_reports.exists():
            scores = [r.scores.get('overall_score', 0) for r in all_reports if r.scores]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            improving_count = all_reports.filter(trend='Improving').values('employee').distinct().count()
            declining_count = all_reports.filter(trend='Declining').values('employee').distinct().count()
            
            # Check confirmation status (e.g., overall score > 80 and at least 3 checklists)
            from django.db.models import Count
            ready_employees = AIReport.objects.values('employee').annotate(
                report_cnt=Count('id')
            ).filter(report_cnt__gte=3)
            for item in ready_employees:
                emp_reports = AIReport.objects.filter(employee_id=item['employee']).order_by('-created_at')
                if emp_reports.exists() and emp_reports[0].scores.get('overall_score', 0) >= 80:
                    ready_for_confirmation += 1

        # Recent activities/submissions
        recent_submissions = ChecklistAssignment.objects.filter(
            status__in=['Submitted', 'Analyzed']
        ).order_by('-submitted_at')[:10]

        submissions_data = []
        for s in recent_submissions:
            report_id = s.ai_report.id if hasattr(s, 'ai_report') else None
            submissions_data.append({
                'id': s.id,
                'employee_name': f"{s.employee.first_name} {s.employee.last_name or ''}".strip(),
                'designation': s.employee.designation or 'Employee',
                'checklist_title': s.checklist.title,
                'submitted_at': s.submitted_at.strftime('%Y-%m-%d %H:%M') if s.submitted_at else 'N/A',
                'status': s.status,
                'score': s.ai_report.scores.get('overall_score', None) if hasattr(s, 'ai_report') else None,
                'report_id': report_id
            })

        return Response({
            'metrics': {
                'total_employees': total_employees,
                'pending_forms': pending_forms,
                'submitted_today': submitted_today,
                'ai_reports_generated': ai_reports_count,
                'average_probation_score': round(avg_score, 1),
                'employees_improving': improving_count,
                'employees_declining': declining_count,
                'employees_ready': ready_for_confirmation
            },
            'recent_submissions': submissions_data
        })


class EmployeeTimelineAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id):
        if not is_admin_or_hr(request.user):
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        employee = get_object_or_404(SyncedEmployee, bitrix_user_id=employee_id)
        assignments = ChecklistAssignment.objects.filter(employee=employee).order_by('assigned_at')

        timeline = []
        for i, assign in enumerate(assignments):
            ai_data = None
            if hasattr(assign, 'ai_report'):
                rep = assign.ai_report
                ai_data = {
                    'overall_score': rep.scores.get('overall_score', 0),
                    'productivity_score': rep.scores.get('productivity_score', 0),
                    'efficiency_score': rep.scores.get('efficiency_score', 0),
                    'consistency_score': rep.scores.get('consistency_score', 0),
                    'trend': rep.trend,
                    'recommendation': rep.recommendation,
                    'summary': rep.summary,
                    'strengths': rep.strengths,
                    'improvements': rep.improvements,
                    'insights': rep.insights,
                    'report_id': rep.id
                }

            timeline.append({
                'label': f"Checkpoint {i + 1}",
                'checklist_title': assign.checklist.title,
                'status': assign.status,
                'assigned_at': assign.assigned_at.strftime('%Y-%m-%d'),
                'submitted_at': assign.submitted_at.strftime('%Y-%m-%d') if assign.submitted_at else None,
                'ai_report': ai_data
            })

        # Check for final consolidated report
        final_report = getattr(employee, 'final_probation_report', None)
        final_report_data = None
        if final_report:
            final_report_data = {
                'average_score': final_report.average_score,
                'best_week': final_report.best_week,
                'lowest_week': final_report.lowest_week,
                'overall_trend': final_report.overall_trend,
                'strengths': final_report.strengths,
                'improvements': final_report.improvements,
                'challenges': final_report.challenges,
                'final_recommendation': final_report.final_recommendation,
                'confidence': final_report.confidence,
                'created_at': final_report.created_at.strftime('%Y-%m-%d')
            }

        return Response({
            'employee_name': f"{employee.first_name} {employee.last_name or ''}".strip(),
            'designation': employee.designation,
            'department': employee.department_name,
            'joining_date': employee.joining_date,
            'timeline': timeline,
            'final_report': final_report_data
        })


class TriggerFinalReportAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, employee_id):
        if not is_admin_or_hr(request.user):
            return Response({"detail": "Permission denied"}, status=status.HTTP_403_FORBIDDEN)

        employee = get_object_or_404(SyncedEmployee, bitrix_user_id=employee_id)
        final_report = run_final_probation_analysis(employee)
        if final_report:
            return Response({
                'message': 'Final probation report generated successfully!',
                'final_report': {
                    'average_score': final_report.average_score,
                    'best_week': final_report.best_week,
                    'lowest_week': final_report.lowest_week,
                    'overall_trend': final_report.overall_trend,
                    'strengths': final_report.strengths,
                    'improvements': final_report.improvements,
                    'challenges': final_report.challenges,
                    'final_recommendation': final_report.final_recommendation,
                    'confidence': final_report.confidence
                }
            })
        else:
            return Response({
                'error': 'Failed to generate final report. Make sure employee has completed checklists analyzed by Gemini.'
            }, status=status.HTTP_400_BAD_REQUEST)


def probation_page_view(request):
    return render(request, 'base/layout.html')

