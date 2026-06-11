import datetime
from django.shortcuts import get_object_or_404, render
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied

from roles.permissions import HasModelPermission
from employee_onboarding.models import Employee, Department
from employee_onboarding.serializers import EmployeeSerializer, EmployeeDocumentSerializer
from .models import ExitRequest, ExitSecureLink, ExitFormResponse
from .serializers import ExitRequestSerializer, ExitFormResponseSerializer
from .services import generate_relieving_letter, generate_experience_letter, generate_notice_letter

class ExitRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ExitRequestSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        return ExitRequest.objects.all().order_by('-initiated_at')

    def perform_create(self, serializer):
        employee = serializer.validated_data['employee']
        
        # Check if employee is already exited
        if employee.status == 'Exited':
            raise ValidationError("This employee has already exited the company.")
            
        resignation_date = serializer.validated_data['resignation_date']
        notice_waiver = serializer.validated_data.get('notice_waiver', False)
        
        # Calculate last working day
        if notice_waiver:
            last_working_day = serializer.validated_data.get(
                'last_working_day',
                resignation_date + datetime.timedelta(days=employee.notice_period_days)
            )
        else:
            last_working_day = resignation_date + datetime.timedelta(days=employee.notice_period_days)
            
        exit_req = serializer.save(
            last_working_day=last_working_day,
            status='PENDING'
        )
        
        # Update employee status to 'In Progress' or exit initiated
        # (We keep employee status Active until exit is fully Completed)
        
        # Create ExitSecureLink
        link = ExitSecureLink.objects.create(exit_request=exit_req)
        
        # Send secure link email
        self._send_email_link(exit_req, link)
        
        # Auto generate Notice Letter if requested
        if exit_req.notice_letter_required:
            generate_notice_letter(exit_req, user=self.request.user)

    def _send_email_link(self, exit_req, link):
        recipient = exit_req.employee.email
        url = f"http://localhost:8000/exit-questionnaire?token={link.token}"
        send_mail(
            subject="Action Required: Exit Clearance Questionnaire",
            message=f"Dear {exit_req.employee.first_name},\n\nPlease complete your offboarding exit clearance form within 7 days by clicking the following link:\n{url}\n\nSincerely,\nHR Department",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False
        )

    @action(detail=True, methods=['POST'], url_path='send-link')
    def send_link_api(self, request, pk=None):
        exit_req = self.get_object()
        # Create fresh link if old ones expired or used
        link = exit_req.secure_links.filter(used=False).first()
        if not link or link.is_expired:
            link = ExitSecureLink.objects.create(exit_request=exit_req)
            
        self._send_email_link(exit_req, link)
        return Response({'message': 'Exit link emailed successfully.'})

    @action(detail=True, methods=['POST'], url_path='generate-relieving')
    def generate_relieving_api(self, request, pk=None):
        exit_req = self.get_object()
        if exit_req.status != 'COMPLETED':
            return Response({
                'error': 'Relieving letter can only be generated after exit process is marked COMPLETED.'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            doc = generate_relieving_letter(exit_req, user=request.user)
            return Response({
                'message': 'Relieving letter generated.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-experience')
    def generate_experience_api(self, request, pk=None):
        exit_req = self.get_object()
        if exit_req.status != 'COMPLETED':
            return Response({
                'error': 'Experience letter can only be generated after exit process is marked COMPLETED.'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            doc = generate_experience_letter(exit_req, user=request.user)
            return Response({
                'message': 'Experience letter generated.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-notice')
    def generate_notice_api(self, request, pk=None):
        exit_req = self.get_object()
        try:
            doc = generate_notice_letter(exit_req, user=request.user)
            return Response({
                'message': 'Notice letter generated.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ExitPublicQuestionnaireView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token_str = request.query_params.get('token')
        if not token_str:
            return Response({'error': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            link = ExitSecureLink.objects.get(token=token_str)
        except (ExitSecureLink.DoesNotExist, ValidationError):
            return Response({'error': 'Invalid exit link token.'}, status=status.HTTP_400_BAD_REQUEST)

        if link.is_expired:
            return Response({'error': 'This exit link has expired or has already been used.'}, status=status.HTTP_400_BAD_REQUEST)

        exit_request = link.exit_request
        employee = exit_request.employee
        
        # Switch exit status to In Progress
        if exit_request.status == 'PENDING':
            exit_request.status = 'IN_PROGRESS'
            exit_request.save()
            
        return Response({
            'exit_request_id': exit_request.id,
            'employee_name': f"{employee.first_name} {employee.last_name}",
            'employee_id': employee.emp_id,
            'last_working_day': exit_request.last_working_day
        })

    def post(self, request):
        token_str = request.data.get('token')
        if not token_str:
            return Response({'error': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            link = ExitSecureLink.objects.get(token=token_str)
        except (ExitSecureLink.DoesNotExist, ValidationError):
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)

        if link.is_expired:
            return Response({'error': 'This link is expired or already used.'}, status=status.HTTP_400_BAD_REQUEST)

        exit_req = link.exit_request
        serializer = ExitFormResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Save questionnaire
        serializer.save(exit_request=exit_req)
        
        # Complete exit requests and links
        exit_req.status = 'COMPLETED'
        exit_req.save()
        
        link.used = True
        link.save()
        
        # Soft delete the employee profile by changing status to 'Exited'
        employee = exit_req.employee
        employee.status = 'Exited'
        employee.save()
        
        return Response({
            'message': 'Your exit questionnaire has been submitted successfully.'
        }, status=status.HTTP_201_CREATED)


class RejoiningAPIView(APIView):
    permission_classes = [IsAuthenticated, HasModelPermission]

    def post(self, request):
        ex_employee_id = request.data.get('ex_employee_id')
        new_joining_date = request.data.get('new_joining_date')
        new_designation = request.data.get('new_designation')
        new_department_id = request.data.get('new_department')
        new_employment_type = request.data.get('new_employment_type')
        new_notice_period_days = request.data.get('new_notice_period_days', 30)
        new_bond_period_months = request.data.get('new_bond_period_months', 0)
        
        # Salary structure payload (nested)
        salary_data = request.data.get('salary_structure')
        
        if not all([ex_employee_id, new_joining_date, new_designation, new_department_id, new_employment_type, salary_data]):
            return Response({'error': 'All details and salary structure are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            ex_employee = Employee.objects.get(id=ex_employee_id, status='Exited')
        except Employee.DoesNotExist:
            return Response({'error': 'Ex-employee record not found.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            dept = Department.objects.get(id=new_department_id)
        except Department.DoesNotExist:
            return Response({'error': 'Department not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Clone employee information and generate a new profile
        new_emp = Employee.objects.create(
            first_name=ex_employee.first_name,
            last_name=ex_employee.last_name,
            email=ex_employee.email, # Wait, email is unique, but the old record is Exited. We can modify old email to allow re-joining, e.g., 'old_email@exited'
            # Let's change old employee email to free the email for the new record
            phone=ex_employee.phone,
            alternate_phone=ex_employee.alternate_phone,
            dob=ex_employee.dob,
            gender=ex_employee.gender,
            address_line1=ex_employee.address_line1,
            address_line2=ex_employee.address_line2,
            city=ex_employee.city,
            state=ex_employee.state,
            pin_code=ex_employee.pin_code,
            department=dept,
            designation=new_designation,
            employment_type=new_employment_type,
            joining_date=new_joining_date,
            notice_period_days=new_notice_period_days,
            bond_period_months=new_bond_period_months,
            emergency_contact_name=ex_employee.emergency_contact_name,
            emergency_relationship=ex_employee.emergency_relationship,
            emergency_phone=ex_employee.emergency_phone,
            aadhaar_encrypted=ex_employee.aadhaar_encrypted,
            pan_encrypted=ex_employee.pan_encrypted,
            status='Active',
            rejoined_from=ex_employee,
            created_by=request.user
        )
        
        # Update old employee record to free the unique email check (e.g. append timestamp to old email)
        timestamp = int(datetime.datetime.now().timestamp())
        ex_employee.email = f"{ex_employee.email}.exited.{timestamp}"
        ex_employee.save()
        
        # Save fresh salary structure
        from salary.models import SalaryStructure
        from salary.serializers import SalaryStructureSerializer
        
        salary_structure_data = salary_data.copy()
        salary_structure_data['employee'] = new_emp.id
        
        # Validate and save salary structure
        salary_serializer = SalaryStructureSerializer(data=salary_structure_data, context={'request': request})
        if not salary_serializer.is_valid():
            # Rollback employee creation if salary structure is invalid
            new_emp.delete()
            # Restore ex employee email
            ex_employee.email = ex_employee.email.split('.exited.')[0]
            ex_employee.save()
            return Response(salary_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        salary_serializer.save(created_by=request.user)

        return Response({
            'message': 'Ex-employee rejoined successfully with a new tenure.',
            'employee': EmployeeSerializer(new_emp).data
        }, status=status.HTTP_201_CREATED)
