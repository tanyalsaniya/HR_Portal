import datetime
import os
import openpyxl
from decimal import Decimal
from django.db import models, transaction
from django.core.files.base import ContentFile
from django.conf import settings
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination

from common.bitrix_client import BitrixClient, BitrixEmployeeMock
from .models import SalaryStructure, SalarySlip, SalaryImportBatch, SalaryIncrementReminder, SalaryIncrementApproval
from .serializers import (
    SalaryStructureSerializer, SalarySlipSerializer, SalaryImportBatchSerializer,
    SalaryIncrementReminderSerializer, SalaryIncrementApprovalSerializer
)
from .services import generate_payslip_pdf, generate_increment_letter_pdf, generate_payslips_zip, num_to_words

# Helper to check roles
def check_role(user):
    if not user or not user.is_authenticated:
        return None
    if user.is_superuser or (user.role and user.role.code == 'ADMIN'):
        return 'admin'
    if user.role and user.role.code == 'HR':
        return 'hr'
    return 'employee'

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

# Legacy viewsets for backward compatibility with UI
class SalaryStructureViewSet(viewsets.ModelViewSet):
    serializer_class = SalaryStructureSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = SalaryStructure.objects.all().order_by('-effective_from')
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        return queryset

    def perform_create(self, serializer):
        # Admin check
        if check_role(self.request.user) != 'admin':
            raise PermissionDenied("Only Admin can manage salary structures.")
        serializer.save()


class SalaryIncrementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

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
        if check_role(request.user) != 'admin':
            raise PermissionDenied("Only Admin can approve increments.")

        reminder = get_object_or_404(SalaryIncrementReminder, pk=pk)
        if reminder.status == 'Actioned':
            return Response({'error': 'This increment reminder has already been actioned.'}, status=status.HTTP_400_BAD_REQUEST)

        bitrix_user_id = reminder.bitrix_user_id
        active_structure = SalaryStructure.objects.filter(bitrix_user_id=bitrix_user_id).order_by('-effective_from').first()
        if not active_structure:
            return Response({'error': 'Active salary structure not found.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = SalaryIncrementApprovalSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        new_basic = serializer.validated_data['new_basic']
        new_hra = serializer.validated_data['new_hra']
        new_allowances = serializer.validated_data['new_allowances']
        effective_date = serializer.validated_data.get('effective_date', reminder.anniversary_date)
        reason = serializer.validated_data['reason']

        old_net = active_structure.net_salary

        new_structure = SalaryStructure.objects.create(
            bitrix_user_id=bitrix_user_id,
            effective_from=effective_date,
            gross_salary=new_basic,
            pf_contribution=active_structure.pf_contribution,
            esi=active_structure.esi,
            labour_welfare_fund=active_structure.labour_welfare_fund,
            professional_tax=active_structure.professional_tax,
            other_deductions=active_structure.other_deductions
        )

        new_net = new_structure.net_salary
        increment_amount = new_net - old_net
        increment_pct = (increment_amount / old_net) * 100 if old_net > 0 else 0

        approval = serializer.save(
            bitrix_user_id=bitrix_user_id,
            reminder=reminder,
            old_net=old_net,
            new_net=new_net,
            increment_amount=increment_amount,
            increment_pct=increment_pct,
            approved_by=request.user
        )

        reminder.status = 'Actioned'
        reminder.actioned_by = request.user
        reminder.actioned_at = timezone.now()
        reminder.save()

        generate_increment_letter_pdf(approval, user=request.user)

        return Response({
            'message': 'Salary increment approved and new structure applied.',
            'approval': SalaryIncrementApprovalSerializer(approval).data
        }, status=status.HTTP_201_CREATED)


# New Endpoints
class SalaryExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if check_role(request.user) != 'admin':
            raise PermissionDenied("Only Admin can export salary sheets.")

        month_param = request.query_params.get('month')
        year_param = request.query_params.get('year')

        if not month_param or not year_param:
            return Response({'error': 'month and year parameters are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            month = int(month_param)
            year = int(year_param)
        except ValueError:
            return Response({'error': 'Invalid month or year.'}, status=status.HTTP_400_BAD_REQUEST)

        # Columns
        headers = [
            "Emp ID", "Emp Name", "Department", "Location", "Gross Salary", 
            "PF Contribution", "ESI", "Labour Welfare Fund", "Professional Tax", 
            "Other Deductions", "Leaves Available", "Working Days", "Leave Encashment / Extra Days"
        ]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = f"Salary_{month}_{year}"
        ws.append(headers)

        # Apply sheet protection
        ws.protection.sheet = True
        ws.protection.password = 'mtlv_payroll'

        from openpyxl.styles import Protection
        locked_style = Protection(locked=True)
        unlocked_style = Protection(locked=False)

        # Check if salary slips already exist
        slips = SalarySlip.objects.filter(month=month, year=year)
        
        # Resolve employees for all slips
        user_map = {}
        for u in BitrixClient.get_all_users():
            user_map[str(u['id'])] = BitrixEmployeeMock(u)
            
        row_idx = 2
        if slips.exists():
            for slip in slips:
                emp = user_map.get(str(slip.bitrix_user_id))
                emp_id = emp.emp_id if emp else f"BITRIX-{slip.bitrix_user_id}"
                emp_name = emp.name if emp else f"User {slip.bitrix_user_id}"
                dept_name = emp.department_name if emp else ""
                row_data = [
                    emp_id,
                    emp_name,
                    dept_name,
                    slip.location,
                    float(slip.gross_salary),
                    float(slip.pf_contribution),
                    float(slip.esi),
                    float(slip.labour_welfare_fund),
                    float(slip.professional_tax),
                    float(slip.other_deductions),
                    float(slip.leaves_available),
                    float(slip.working_days),
                    float(slip.extra_days)
                ]
                ws.append(row_data)
                
                # Lock A, B, C (1, 2, 3), unlock others
                for col_idx in range(1, 14):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    if col_idx in [1, 2, 3]:
                        cell.protection = locked_style
                    else:
                        cell.protection = unlocked_style
                row_idx += 1
        else:
            # Export empty template using active employees & structures
            users = BitrixClient.get_all_users()
            employees = [BitrixEmployeeMock(u) for u in users if BitrixEmployeeMock(u).status != 'Exited']
            for emp in employees:
                struct = SalaryStructure.objects.filter(bitrix_user_id=emp.bitrix_id, effective_from__lte=datetime.date(year, month, 28)).order_by('-effective_from').first()
                if not struct:
                    # Fallback to absolute latest if none effective yet
                    struct = SalaryStructure.objects.filter(bitrix_user_id=emp.bitrix_id).order_by('-effective_from').first()

                row_data = [
                    emp.emp_id,
                    emp.name,
                    emp.department.name if emp.department else "",
                    "Mohali",
                    float(struct.gross_salary) if struct else 0.0,
                    float(struct.pf_contribution) if struct else 0.0,
                    float(struct.esi) if struct else 0.0,
                    float(struct.labour_welfare_fund) if struct else 0.0,
                    float(struct.professional_tax) if struct else 0.0,
                    float(struct.other_deductions) if struct else 0.0,
                    "",  # Leaves Available (blank)
                    "",  # Working Days (blank)
                    ""   # Extra Days (blank)
                ]
                ws.append(row_data)

                for col_idx in range(1, 14):
                    cell = ws.cell(row=row_idx, column=col_idx)
                    if col_idx in [1, 2, 3]:
                        cell.protection = locked_style
                    else:
                        cell.protection = unlocked_style
                row_idx += 1

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = f'attachment; filename="salary_sheet_{month}_{year}.xlsx"'
        wb.save(response)
        return response


class SalaryImportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if check_role(request.user) != 'admin':
            raise PermissionDenied("Only Admin can import salary sheets.")

        file_obj = request.FILES.get('file')
        month_str = request.data.get('month')
        year_str = request.data.get('year')

        if not file_obj or not month_str or not year_str:
            return Response({'error': 'file, month, and year are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            month = int(month_str)
            year = int(year_str)
            if not (1 <= month <= 12):
                raise ValueError()
        except ValueError:
            return Response({'error': 'Invalid month or year.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Create batch
        batch = SalaryImportBatch.objects.create(
            month=month,
            year=year,
            file_name=file_obj.name,
            uploaded_by=request.user,
            status='processing'
        )

        try:
            wb = openpyxl.load_workbook(file_obj, data_only=True)
            ws = wb.active
        except Exception as e:
            batch.status = 'failed'
            batch.save()
            return Response({'error': f'Failed to parse Excel file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        # Parsers
        def parse_decimal(val, col_name):
            if val is None or str(val).strip() == "":
                return Decimal("0.00")
            try:
                cleaned = str(val).strip().replace("$", "").replace(",", "")
                d = Decimal(cleaned)
                if d < 0:
                    raise ValueError()
                return d
            except Exception:
                raise ValueError(f"Invalid value in column {col_name}")

        headers = [
            "Emp ID", "Emp Name", "Department", "Location", "Gross Salary", 
            "PF Contribution", "ESI", "Labour Welfare Fund", "Professional Tax", 
            "Other Deductions", "Leaves Available", "Working Days", "Leave Encashment / Extra Days"
        ]

        total_records = 0
        success_count = 0
        failed_count = 0
        failed_rows_data = []

        try:
            with transaction.atomic():
                for r_idx in range(2, ws.max_row + 1):
                    emp_id_val = ws.cell(row=r_idx, column=1).value
                    if emp_id_val is None or str(emp_id_val).strip() == "":
                        continue

                    total_records += 1
                    row_vals = [ws.cell(row=r_idx, column=c).value for c in range(1, 14)]
                    emp_id = str(emp_id_val).strip()

                    sid = transaction.savepoint()
                    try:
                        # Validate Employee
                        bitrix_users = BitrixClient.get_all_users()
                        employee = None
                        for u in bitrix_users:
                            mock_emp = BitrixEmployeeMock(u)
                            if mock_emp.emp_id == emp_id or str(mock_emp.bitrix_id) == str(emp_id):
                                employee = mock_emp
                                break
                        if not employee or employee.status == 'Exited':
                            raise ValueError("Employee is exited or not found in Bitrix24")

                        # Parse data
                        location = str(ws.cell(row=r_idx, column=4).value or "Mohali").strip()
                        gross_salary = parse_decimal(ws.cell(row=r_idx, column=5).value, "Gross Salary")
                        pf_contribution = parse_decimal(ws.cell(row=r_idx, column=6).value, "PF Contribution")
                        esi = parse_decimal(ws.cell(row=r_idx, column=7).value, "ESI")
                        labour_welfare_fund = parse_decimal(ws.cell(row=r_idx, column=8).value, "Labour Welfare Fund")
                        professional_tax = parse_decimal(ws.cell(row=r_idx, column=9).value, "Professional Tax")
                        other_deductions = parse_decimal(ws.cell(row=r_idx, column=10).value, "Other Deductions")
                        leaves_available = parse_decimal(ws.cell(row=r_idx, column=11).value, "Leaves Available")
                        working_days = parse_decimal(ws.cell(row=r_idx, column=12).value, "Working Days")
                        extra_days = parse_decimal(ws.cell(row=r_idx, column=13).value, "Leave Encashment / Extra Days")

                        # Save SalarySlip
                        slip = SalarySlip.objects.filter(bitrix_user_id=employee.bitrix_id, month=month, year=year).first()
                        if slip:
                            slip.location = location
                            slip.gross_salary = gross_salary
                            slip.pf_contribution = pf_contribution
                            slip.esi = esi
                            slip.labour_welfare_fund = labour_welfare_fund
                            slip.professional_tax = professional_tax
                            slip.other_deductions = other_deductions
                            slip.leaves_available = leaves_available
                            slip.working_days = working_days
                            slip.extra_days = extra_days
                            slip.status = 'draft' # Re-review needed
                            slip.uploaded_batch = batch
                            slip.save()
                        else:
                            slip = SalarySlip.objects.create(
                                bitrix_user_id=employee.bitrix_id,
                                month=month,
                                year=year,
                                location=location,
                                gross_salary=gross_salary,
                                pf_contribution=pf_contribution,
                                esi=esi,
                                labour_welfare_fund=labour_welfare_fund,
                                professional_tax=professional_tax,
                                other_deductions=other_deductions,
                                leaves_available=leaves_available,
                                working_days=working_days,
                                extra_days=extra_days,
                                status='draft',
                                uploaded_batch=batch
                            )
                        
                        generate_payslip_pdf(slip)
                        transaction.savepoint_commit(sid)
                        success_count += 1
                    except Exception as e:
                        transaction.savepoint_rollback(sid)
                        failed_count += 1
                        failed_rows_data.append((row_vals, str(e)))

                if failed_count == total_records and total_records > 0:
                    raise Exception("All rows failed validation")
        except Exception as batch_err:
            # Batch fully failed rollback occurred
            batch.status = 'failed'
            batch.total_records = total_records
            batch.success_count = 0
            batch.failed_count = total_records
            
            error_report_url = self.generate_error_xlsx(batch.id, headers, failed_rows_data)
            batch.error_report_path = error_report_url
            batch.save()
            return Response({
                "total": total_records,
                "success": 0,
                "failed": total_records,
                "error_report_url": error_report_url,
                "detail": str(batch_err)
            }, status=status.HTTP_400_BAD_REQUEST)

        # Batch committed
        if failed_count > 0:
            batch.status = 'partial'
            error_report_url = self.generate_error_xlsx(batch.id, headers, failed_rows_data)
            batch.error_report_path = error_report_url
        else:
            batch.status = 'success'
            error_report_url = None

        batch.total_records = total_records
        batch.success_count = success_count
        batch.failed_count = failed_count
        batch.save()

        return Response({
            "total": total_records,
            "success": success_count,
            "failed": failed_count,
            "error_report_url": error_report_url
        }, status=status.HTTP_200_OK)

    def generate_error_xlsx(self, batch_id, headers, failed_rows_data):
        error_report_dir = os.path.join(settings.MEDIA_ROOT, "error_reports")
        os.makedirs(error_report_dir, exist_ok=True)
        report_filename = f"error_report_{batch_id}_{int(datetime.datetime.now().timestamp())}.xlsx"
        report_path = os.path.join(error_report_dir, report_filename)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Errors"
        ws.append(headers + ["Error Reason"])

        for row_vals, reason in failed_rows_data:
            ws.append(row_vals + [reason])

        wb.save(report_path)
        return f"{settings.MEDIA_URL}error_reports/{report_filename}"


class SalaryPublishView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if check_role(request.user) != 'admin':
            raise PermissionDenied("Only Admin can publish slips.")

        month_str = request.data.get('month')
        year_str = request.data.get('year')

        if not month_str or not year_str:
            return Response({'error': 'month and year are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            month = int(month_str)
            year = int(year_str)
        except ValueError:
            return Response({'error': 'Invalid month or year.'}, status=status.HTTP_400_BAD_REQUEST)

        slips = SalarySlip.objects.filter(month=month, year=year, status='draft')
        count = slips.count()
        for slip in slips:
            slip.status = 'published'
            slip.save()
            generate_payslip_pdf(slip)

        return Response({'message': f'Successfully published {count} salary slips.'}, status=status.HTTP_200_OK)


class SalaryEditView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        if check_role(request.user) != 'admin':
            raise PermissionDenied("Only Admin can edit salary slips.")

        slip = get_object_or_404(SalarySlip, pk=pk)

        # Exclude read-only calculations from direct parsing
        mutable_fields = [
            'location', 'leaves_available', 'working_days', 'extra_days',
            'gross_salary', 'pf_contribution', 'esi', 'labour_welfare_fund',
            'professional_tax', 'other_deductions', 'net_credited_amount',
            'payment_status', 'payment_date', 'transaction_ref'
        ]

        for field in mutable_fields:
            if field in request.data:
                val = request.data[field]
                if field in ['payment_status', 'transaction_ref', 'location']:
                    setattr(slip, field, val)
                elif field == 'payment_date':
                    setattr(slip, field, val if val else None)
                else:
                    setattr(slip, field, Decimal(str(val)) if val else Decimal('0.00'))

        slip.status = 'draft' # Re-review needed after edit
        slip.save()
        generate_payslip_pdf(slip)

        serializer = SalarySlipSerializer(slip)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SalaryHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        role = check_role(request.user)
        
        # Scoped logic
        if role == 'employee':
            # Force self
            user_data = next((u for u in BitrixClient.get_all_users() if u.get('email') == request.user.email), None)
            if not user_data:
                return Response({'error': 'Employee profile not found in Bitrix24.'}, status=status.HTTP_404_NOT_FOUND)
            employee = BitrixEmployeeMock(user_data)
            slips = SalarySlip.objects.filter(bitrix_user_id=employee.bitrix_id, status='published').order_by('-year', '-month')
        else:
            # Admin / HR
            employee_id = request.query_params.get('employee_id') or kwargs.get('employee_id') or request.query_params.get('bitrix_user_id')
            if employee_id:
                slips = SalarySlip.objects.filter(bitrix_user_id=str(employee_id)).order_by('-year', '-month')
            else:
                # Paginate all employees slips
                slips = SalarySlip.objects.all().order_by('-year', '-month')

        # Payment status filtering
        payment_status = request.query_params.get('payment_status')
        if payment_status:
            slips = slips.filter(payment_status=payment_status)

        # Date range filtering
        from_param = request.query_params.get('from') # format: YYYY-MM
        to_param = request.query_params.get('to')     # format: YYYY-MM

        if from_param:
            try:
                fY, fM = map(int, from_param.split('-'))
                slips = slips.filter(
                    models.Q(year__gt=fY) | models.Q(year=fY, month__gte=fM)
                )
            except ValueError:
                pass

        if to_param:
            try:
                tY, tM = map(int, to_param.split('-'))
                slips = slips.filter(
                    models.Q(year__lt=tY) | models.Q(year=tY, month__lte=tM)
                )
            except ValueError:
                pass

        # Pagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(slips, request, view=self)
        
        bitrix_users = {str(u['id']): BitrixEmployeeMock(u) for u in BitrixClient.get_all_users()}
        data = []
        target_list = page if page is not None else slips
        for s in target_list:
            emp = bitrix_users.get(str(s.bitrix_user_id))
            emp_id = emp.id if emp else 0
            emp_name = emp.name if emp else f"User {s.bitrix_user_id}"
            data.append({
                'id': s.id,
                'employee_id': emp_id,
                'employee_name': emp_name,
                'month': s.month,
                'year': s.year,
                'location': s.location,
                'leaves_available': str(s.leaves_available),
                'working_days': str(s.working_days),
                'extra_days': str(s.extra_days),
                'gross_salary': str(s.gross_salary),
                'pf_contribution': str(s.pf_contribution),
                'esi': str(s.esi),
                'labour_welfare_fund': str(s.labour_welfare_fund),
                'professional_tax': str(s.professional_tax),
                'other_deductions': str(s.other_deductions),
                'total_deductions': str(s.total_deductions),
                'net_salary': str(s.net_salary),
                'net_credited_amount': str(s.net_credited_amount),
                'payment_status': s.payment_status,
                'payment_date': str(s.payment_date) if s.payment_date else '',
                'transaction_ref': s.transaction_ref or '',
                'status': s.status
            })

        if page is not None:
            return paginator.get_paginated_response(data)
        return Response(data)


class SalarySlipDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = check_role(request.user)

        employee_id = request.query_params.get('employee_id')
        download_type = request.query_params.get('type') # single | last3 | last4 | range | bulk_month | selected

        if role == 'employee':
            user_data = next((u for u in BitrixClient.get_all_users() if u.get('email') == request.user.email), None)
            if not user_data:
                return Response({'error': 'Employee profile not found.'}, status=status.HTTP_404_NOT_FOUND)
            employee = BitrixEmployeeMock(user_data)
            employee_id = employee.bitrix_id
            # Employees can only download published slips
            slips_qs = SalarySlip.objects.filter(bitrix_user_id=employee_id, status='published')
        else:
            # Admin/HR
            if download_type in ['bulk_month', 'selected'] and not employee_id:
                slips_qs = SalarySlip.objects.all()
            else:
                if not employee_id:
                    return Response({'error': 'employee_id parameter is required for Admin/HR.'}, status=status.HTTP_400_BAD_REQUEST)
                slips_qs = SalarySlip.objects.filter(bitrix_user_id=str(employee_id))

        # Filters
        slips = []
        if download_type == 'single':
            month_str = request.query_params.get('month')
            year_str = request.query_params.get('year')
            if not month_str or not year_str:
                return Response({'error': 'month and year are required.'}, status=status.HTTP_400_BAD_REQUEST)
            slips = slips_qs.filter(month=int(month_str), year=int(year_str))
        elif download_type == 'last3':
            slips = slips_qs.order_by('-year', '-month')[:3]
        elif download_type == 'last4':
            slips = slips_qs.order_by('-year', '-month')[:4]
        elif download_type == 'range':
            from_month = int(request.query_params.get('from_month', 1))
            from_year = int(request.query_params.get('from_year', 2000))
            to_month = int(request.query_params.get('to_month', 12))
            to_year = int(request.query_params.get('to_year', 2100))
            
            # Filters BETWEEN from and to inclusive
            slips = slips_qs.filter(
                models.Q(year__gt=from_year) | models.Q(year=from_year, month__gte=from_month)
            ).filter(
                models.Q(year__lt=to_year) | models.Q(year=to_year, month__lte=to_month)
            ).order_by('year', 'month')
        elif download_type == 'bulk_month':
            if role not in ['admin', 'hr']:
                raise PermissionDenied("Only Admin/HR can bulk download slips.")
            month_str = request.query_params.get('month')
            year_str = request.query_params.get('year')
            if not month_str or not year_str:
                return Response({'error': 'month and year are required.'}, status=status.HTTP_400_BAD_REQUEST)
            slips = slips_qs.filter(month=int(month_str), year=int(year_str))
        elif download_type == 'selected':
            slip_ids_str = request.query_params.get('slip_ids')
            if not slip_ids_str:
                return Response({'error': 'slip_ids parameter is required for type=selected.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                ids = [int(x) for x in slip_ids_str.split(',')]
                slips = slips_qs.filter(id__in=ids)
            except ValueError:
                return Response({'error': 'Invalid slip_ids parameter.'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'Invalid download type.'}, status=status.HTTP_400_BAD_REQUEST)

        slips = list(slips)
        if not slips:
            return Response({'error': 'No salary slips found matching parameters.'}, status=status.HTTP_404_NOT_FOUND)

        if len(slips) == 1:
            slip = slips[0]
            # Ensure PDF exists
            generate_payslip_pdf(slip)
            
            # Serve single PDF
            response = HttpResponse(slip.pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="payslip_{slip.employee.emp_id}_{slip.month}_{slip.year}.pdf"'
            return response
        else:
            # Serve ZIP
            zip_type = 'bulk' if download_type == 'bulk_month' else 'employee'
            zip_data = generate_payslips_zip(slips, zip_type)
            
            response = HttpResponse(zip_data, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="payslips_{int(datetime.datetime.now().timestamp())}.zip"'
            return response


class SalaryImportBatchesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if check_role(request.user) != 'admin':
            raise PermissionDenied("Only Admin can view import batches.")

        batches = SalaryImportBatch.objects.all().order_by('-uploaded_at')
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(batches, request, view=self)
        serializer = SalaryImportBatchSerializer(page if page is not None else batches, many=True)
        
        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)


class SalaryEmployeeSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id):
        role = check_role(request.user)
        if role == 'employee':
            # Employees can only view their own summary
            employee = Employee.objects.filter(email=request.user.email, is_deleted=False).first()
            if not employee or employee.id != employee_id:
                raise PermissionDenied("You can only view your own salary summary.")

        slips = SalarySlip.objects.filter(employee_id=employee_id)
        
        total_credited = slips.aggregate(models.Sum('net_credited_amount'))['net_credited_amount__sum'] or Decimal('0.00')
        total_deductions = slips.aggregate(models.Sum('total_deductions'))['total_deductions__sum'] or Decimal('0.00')
        total_payslips = slips.count()
        last_paid_slip = slips.filter(payment_status='paid', payment_date__isnull=False).order_by('-payment_date').first()
        last_payment_date = last_paid_slip.payment_date.strftime('%Y-%m-%d') if last_paid_slip else '-'

        return Response({
            'total_salary_credited': str(total_credited),
            'total_deductions': str(total_deductions),
            'total_payslips': total_payslips,
            'last_payment_date': last_payment_date
        })


class SalaryEmployeeHistoryExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, employee_id):
        role = check_role(request.user)
        if role == 'employee':
            employee = Employee.objects.filter(email=request.user.email, is_deleted=False).first()
            if not employee or employee.id != employee_id:
                raise PermissionDenied("You can only export your own salary history.")
        else:
            employee = get_object_or_404(Employee, id=employee_id, is_deleted=False)

        slips = SalarySlip.objects.filter(employee=employee).order_by('-year', '-month')

        from_param = request.query_params.get('from')
        to_param = request.query_params.get('to')
        payment_status = request.query_params.get('payment_status')

        if from_param:
            try:
                fY, fM = map(int, from_param.split('-'))
                slips = slips.filter(models.Q(year__gt=fY) | models.Q(year=fY, month__gte=fM))
            except ValueError:
                pass
        if to_param:
            try:
                tY, tM = map(int, to_param.split('-'))
                slips = slips.filter(models.Q(year__lt=tY) | models.Q(year=tY, month__lte=tM))
            except ValueError:
                pass
        if payment_status:
            slips = slips.filter(payment_status=payment_status)

        headers = [
            "Month/Year", "Location", "Gross Salary", "PF Contribution", "ESI", 
            "Labour Welfare Fund", "Professional Tax", "Other Deductions", "Leaves Available", 
            "Working Days", "Leave Encashment / Extra Days", "Total Deductions", "Net Salary", 
            "Net Credited Amount", "Payment Status", "Payment Date", "Transaction Ref"
        ]

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Salary History"
        ws.append(headers)

        month_names = ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

        for s in slips:
            ws.append([
                f"{month_names[s.month]} {s.year}",
                s.location,
                float(s.gross_salary),
                float(s.pf_contribution),
                float(s.esi),
                float(s.labour_welfare_fund),
                float(s.professional_tax),
                float(s.other_deductions),
                float(s.leaves_available),
                float(s.working_days),
                float(s.extra_days),
                float(s.total_deductions),
                float(s.net_salary),
                float(s.net_credited_amount),
                s.payment_status.capitalize(),
                s.payment_date.strftime('%Y-%m-%d') if s.payment_date else '',
                s.transaction_ref or ''
            ])

        response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        response['Content-Disposition'] = f'attachment; filename="salary_history_{employee.emp_id}.xlsx"'
        wb.save(response)
        return response
