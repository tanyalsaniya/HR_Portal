import datetime
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError

from roles.permissions import HasModelPermission
from common.utils import generate_payslip_number
from employee_onboarding.models import Employee
from .models import SalaryStructure, SalarySlip, SalaryIncrementReminder, SalaryIncrementApproval
from .serializers import (
    SalaryStructureSerializer, SalarySlipSerializer,
    SalaryIncrementReminderSerializer, SalaryIncrementApprovalSerializer
)
from .services import calculate_payslip_details, generate_payslip_pdf, generate_increment_letter_pdf
from rules import ROLE_ADMIN

class SalaryStructureViewSet(viewsets.ModelViewSet):
    serializer_class = SalaryStructureSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        queryset = SalaryStructure.objects.all().order_by('-effective_from')
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        return queryset


class SalarySlipViewSet(viewsets.ModelViewSet):
    serializer_class = SalarySlipSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        queryset = SalarySlip.objects.all().order_by('-year', '-month')
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        employee = serializer.validated_data['employee']
        month = serializer.validated_data['month']
        year = serializer.validated_data['year']
        working_days = serializer.validated_data['working_days']
        days_worked = serializer.validated_data['days_worked']
        one_time_bonus = serializer.validated_data.get('one_time_bonus', 0)
        one_time_deduction = serializer.validated_data.get('one_time_deduction', 0)
        
        # Check if payslip already exists for this employee/month/year
        if SalarySlip.objects.filter(employee=employee, month=month, year=year).exists():
            raise ValidationError(f"A payslip already exists for this employee for {month}/{year}.")
            
        # Calculate salary slip components
        try:
            details = calculate_payslip_details(
                employee=employee,
                year=year,
                month=month,
                working_days=working_days,
                days_worked=days_worked,
                one_time_bonus=one_time_bonus,
                one_time_deduction=one_time_deduction
            )
        except ValueError as e:
            raise ValidationError(str(e))
            
        # Generate Payslip number
        payslip_no = generate_payslip_number(year, month)
        
        # Save slip details
        slip = serializer.save(
            payslip_no=payslip_no,
            lop_days=details['lop_days'],
            gross=details['gross'],
            total_deductions=details['total_deductions'],
            net_pay=details['net_pay'],
            generated_by=self.request.user
        )
        
        # Generate PDF
        generate_payslip_pdf(slip, details, user=self.request.user)

    @action(detail=False, methods=['POST'], url_path='bulk-generate')
    @transaction.atomic
    def bulk_generate(self, request):
        month = request.data.get('month')
        year = request.data.get('year')
        working_days = request.data.get('working_days')
        payment_date = request.data.get('payment_date')
        payment_mode = request.data.get('payment_mode', 'BANK_TRANSFER')

        if not all([month, year, working_days, payment_date]):
            return Response({'error': 'month, year, working_days, and payment_date are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Get all active employees
        active_employees = Employee.objects.filter(status='Active', is_deleted=False)
        generated_count = 0
        skipped_count = 0

        for employee in active_employees:
            # Check if payslip already exists
            if SalarySlip.objects.filter(employee=employee, month=month, year=year).exists():
                skipped_count += 1
                continue

            # Check if salary structure exists
            structure = SalaryStructure.objects.filter(employee=employee).order_by('-effective_from').first()
            if not structure:
                skipped_count += 1
                continue

            # For bulk, assume employee worked all days (no LOP)
            details = calculate_payslip_details(
                employee=employee,
                year=int(year),
                month=int(month),
                working_days=int(working_days),
                days_worked=int(working_days)
            )

            payslip_no = generate_payslip_number(year, month)
            
            slip = SalarySlip.objects.create(
                employee=employee,
                payslip_no=payslip_no,
                month=int(month),
                year=int(year),
                working_days=int(working_days),
                days_worked=int(working_days),
                lop_days=0,
                gross=details['gross'],
                total_deductions=details['total_deductions'],
                net_pay=details['net_pay'],
                payment_date=payment_date,
                payment_mode=payment_mode,
                generated_by=request.user
            )

            # Generate PDF
            generate_payslip_pdf(slip, details, user=request.user)
            generated_count += 1

        return Response({
            'message': f"Bulk payslip generation completed.",
            'generated': generated_count,
            'skipped': skipped_count
        }, status=status.HTTP_201_CREATED)
class SalaryIncrementViewSet(viewsets.ModelViewSet):
    permission_classes = [HasModelPermission]

    def get_serializer_class(self):
        if self.action == 'approve':
            return SalaryIncrementApprovalSerializer
        return SalaryIncrementReminderSerializer

    def get_queryset(self):
        if self.action in ('list_approvals', 'retrieve_approval'):
            return SalaryIncrementApproval.objects.all().order_by('-approved_at')
        return SalaryIncrementReminder.objects.all().order_by('-anniversary_date')

    @action(detail=False, methods=['GET'], url_path='approvals')
    def list_approvals(self, request):
        queryset = SalaryIncrementApproval.objects.all().order_by('-approved_at')
        serializer = SalaryIncrementApprovalSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['POST'], url_path='approve')
    @transaction.atomic
    def approve(self, request, pk=None):
        # Admin or permission validation
        is_admin = request.user.is_superuser or (request.user.role and request.user.role.code == 'ADMIN')
        has_perm = request.user.role and request.user.role.permissions.filter(codename='salary.approve_increments').exists()
        if not (is_admin or has_perm):
            raise PermissionDenied("Only Admin users or roles with increment approval permission can approve salary increments.")

        reminder = self.get_object()
        if reminder.status == 'Actioned':
            return Response({'error': 'This increment reminder has already been actioned.'}, status=status.HTTP_400_BAD_REQUEST)

        employee = reminder.employee
        active_structure = SalaryStructure.objects.filter(employee=employee).order_by('-effective_from').first()
        if not active_structure:
            return Response({'error': 'Active salary structure not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Deserialize input fields
        serializer = SalaryIncrementApprovalSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        new_basic = serializer.validated_data['new_basic']
        new_hra = serializer.validated_data['new_hra']
        new_allowances = serializer.validated_data['new_allowances'] # parsed allowances amount
        effective_date = serializer.validated_data.get('effective_date', reminder.anniversary_date)
        reason = serializer.validated_data['reason']

        # Calculate difference
        old_net = active_structure.net_salary
        
        # Build temp structure to calculate new net
        temp_struct = SalaryStructure(
            employee=employee,
            basic=new_basic,
            hra=new_hra,
            conveyance=active_structure.conveyance,
            medical=active_structure.medical,
            special=new_allowances, # Add raises in special allowance
            pf=active_structure.pf,
            professional_tax=active_structure.professional_tax,
            tds=active_structure.tds
        )
        new_net = temp_struct.net_salary
        increment_amount = new_net - old_net
        increment_pct = (increment_amount / old_net) * 100 if old_net > 0 else 0

        # Save new SalaryStructure in database
        new_structure = SalaryStructure.objects.create(
            employee=employee,
            effective_from=effective_date,
            basic=new_basic,
            hra=new_hra,
            conveyance=active_structure.conveyance,
            medical=active_structure.medical,
            special=new_allowances,
            pf=active_structure.pf,
            professional_tax=active_structure.professional_tax,
            tds=active_structure.tds,
            other_allowances=active_structure.other_allowances,
            other_deductions=active_structure.other_deductions,
            created_by=request.user
        )

        # Save approval record
        approval = serializer.save(
            employee=employee,
            reminder=reminder,
            old_net=old_net,
            new_net=new_net,
            increment_amount=increment_amount,
            increment_pct=increment_pct,
            approved_by=request.user
        )

        # Mark reminder as Actioned
        reminder.status = 'Actioned'
        reminder.actioned_by = request.user
        reminder.actioned_at = datetime.datetime.now()
        reminder.save()

        # Compile PDF Letter
        generate_increment_letter_pdf(approval, user=request.user)

        # Email letter to employee
        self._email_increment_letter(approval)

        return Response({
            'message': 'Salary increment approved and new structure applied.',
            'approval': SalaryIncrementApprovalSerializer(approval).data
        }, status=status.HTTP_201_CREATED)

    def _email_increment_letter(self, approval):
        recipient = approval.employee.email
        send_mail(
            subject="Congratulations: Salary Increment Review Approved",
            message=f"Dear {approval.employee.first_name},\n\nWe are pleased to inform you that your salary review has been completed and approved by the management. Your salary increment letter has been generated.\n\nEffective Date: {approval.effective_date}\n\nSincerely,\nHR Management",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False
        )
