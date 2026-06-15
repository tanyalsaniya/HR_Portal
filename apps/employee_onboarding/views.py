from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from roles.permissions import HasModelPermission
from rules import ROLE_ADMIN
from django.db import models
from .models import Department, Employee, EmployeeDocument, LetterTemplate
from .serializers import DepartmentSerializer, EmployeeSerializer, EmployeeDocumentSerializer, LetterTemplateSerializer
from .services import generate_offer_letter, generate_appointment_letter, generate_bond_letter
import os
import mimetypes
from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

class SecureDocumentServeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, emp_id, filename):
        user = request.user
        is_authorized = user.is_superuser or (user.role and user.role.code in ['ADMIN', 'HR'])
        if not is_authorized:
            raise PermissionDenied("You do not have permission to access employee documents.")

        # Resolve path
        file_path = os.path.join(settings.MEDIA_ROOT, 'employees', emp_id, 'docs', filename)
        normalized_path = os.path.normpath(file_path)
        
        # Prevent directory traversal
        if not normalized_path.startswith(os.path.normpath(settings.MEDIA_ROOT)):
            raise PermissionDenied("Access denied.")

        if not os.path.exists(normalized_path) or os.path.isdir(normalized_path):
            raise Http404("Document not found.")

        mime_type, _ = mimetypes.guess_type(normalized_path)
        if not mime_type:
            mime_type = 'application/octet-stream'

        return FileResponse(open(normalized_path, 'rb'), content_type=mime_type)

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all().order_by('name')
    serializer_class = DepartmentSerializer
    permission_classes = [HasModelPermission]

class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        import datetime
        queryset = Employee.objects.filter(is_deleted=False).order_by('-created_at')
        
        # Split List logic
        list_type = self.request.query_params.get('type')
        today = datetime.date.today()
        
        if list_type == 'onboarding':
            # Day 1-15: onboarding_complete is False
            queryset = queryset.filter(onboarding_complete=False)
        elif list_type == 'all':
            # Day 15: appears in BOTH (so joining_date <= today - 14 days)
            # Day 16+: onboarding_complete is True
            # Or manually completed
            day_14_ago = today - datetime.timedelta(days=14)
            queryset = queryset.filter(
                models.Q(onboarding_complete=True) | models.Q(joining_date__lte=day_14_ago)
            )
            
        return queryset

    def perform_create(self, serializer):
        emp = serializer.save()
        # Trigger background Bitrix24 contact sync task
        from .tasks import sync_employee_to_bitrix24
        sync_employee_to_bitrix24.delay(emp.id)

    def perform_update(self, serializer):
        emp = serializer.save()
        # Trigger background Bitrix24 contact update task
        from .tasks import sync_employee_to_bitrix24
        sync_employee_to_bitrix24.delay(emp.id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['POST'], url_path='manual-graduate')
    def manual_graduate(self, request, pk=None):
        employee = self.get_object()
        if employee.onboarding_complete:
            return Response({'message': 'Employee is already graduated.'}, status=status.HTTP_400_BAD_REQUEST)
        
        employee.onboarding_complete = True
        employee.save()
        
        # Trigger Bitrix24 update
        from .tasks import update_bitrix24_onboarding_status
        update_bitrix24_onboarding_status.delay(employee.id)
        
        # Write to Audit Log
        from audit_logs.signals import log_action
        log_action(request.user, "GRADUATE", employee, f"Employee onboarding manually marked complete before Day 15.")
        
        return Response({'message': 'Employee onboarding completed successfully.'})

    @action(detail=True, methods=['POST'], url_path='retry-bitrix-sync')
    def retry_bitrix_sync(self, request, pk=None):
        employee = self.get_object()
        from .tasks import sync_employee_to_bitrix24
        sync_employee_to_bitrix24.delay(employee.id)
        return Response({'message': 'Bitrix24 sync task queued.'})

    @action(detail=True, methods=['POST'], url_path='generate-offer-letter')
    def generate_offer_letter_api(self, request, pk=None):
        employee = self.get_object()
        custom_context = request.data.get('custom_context', None)
        try:
            doc = generate_offer_letter(employee, user=request.user, custom_context=custom_context)
            # Sync to Bitrix24 timeline
            from .tasks import attach_document_to_bitrix24_timeline
            attach_document_to_bitrix24_timeline.delay(doc.id)
            return Response({
                'message': 'Offer letter generated successfully.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-appointment-letter')
    def generate_appointment_letter_api(self, request, pk=None):
        employee = self.get_object()
        custom_context = request.data.get('custom_context', None)
        try:
            doc = generate_appointment_letter(employee, user=request.user, custom_context=custom_context)
            # Sync to Bitrix24 timeline
            from .tasks import attach_document_to_bitrix24_timeline
            attach_document_to_bitrix24_timeline.delay(doc.id)
            return Response({
                'message': 'Appointment letter generated successfully.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-bond-letter')
    def generate_bond_letter_api(self, request, pk=None):
        employee = self.get_object()
        custom_context = request.data.get('custom_context', None)
        
        bond_period = employee.bond_period_months
        if custom_context and 'bond_period_months' in custom_context:
            try:
                bond_period = int(custom_context['bond_period_months'] or 0)
            except ValueError:
                pass
                
        if bond_period <= 0:
            return Response({
                'error': 'This employee does not have a bond period specified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            doc = generate_bond_letter(employee, user=request.user, custom_context=custom_context)
            # Sync to Bitrix24 timeline
            from .tasks import attach_document_to_bitrix24_timeline
            attach_document_to_bitrix24_timeline.delay(doc.id)
            return Response({
                'message': 'Bond letter generated successfully.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='preview-letter')
    def preview_letter_api(self, request, pk=None):
        employee = self.get_object()
        doc_type = request.data.get('doc_type', None)
        custom_context = request.data.get('custom_context', None)
        
        if not doc_type:
            return Response({'error': 'doc_type is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            from .services import render_letter_to_html
            html_string = render_letter_to_html(employee, doc_type, custom_context)
            return Response({'html': html_string})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'], url_path='import-excel')
    def excel_import(self, request):
        import openpyxl
        import datetime
        from django.db import transaction
        from openpyxl import Workbook
        from django.http import HttpResponse

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            wb = openpyxl.load_workbook(file_obj)
            sheet = wb.active
        except Exception as e:
            return Response({'error': f"Failed to read file: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        rows = list(sheet.iter_rows(min_row=2, values_only=True))
        errors_occurred = False
        parsed_employees = []
        error_rows = []

        for row_idx, row in enumerate(rows, start=2):
            if not any(row):
                continue

            try:
                first_name, last_name, email, phone, dob, gender, address, city, state, pin, dept_name, designation, emp_type, joining_date, notice_period, bond_period, emergency_name, emergency_rel, emergency_phone = row[:19]
            except Exception as e:
                error_rows.append(list(row) + [f"Invalid column count: {e}"])
                errors_occurred = True
                continue

            row_errors = {}
            dept = None
            if dept_name:
                try:
                    dept = Department.objects.get(name__iexact=str(dept_name).strip())
                except Department.DoesNotExist:
                    row_errors['department'] = f"Department '{dept_name}' does not exist in master."

            def clean_date(d_val):
                if isinstance(d_val, datetime.date):
                    return d_val
                if isinstance(d_val, str):
                    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d'):
                        try:
                            return datetime.datetime.strptime(d_val.strip(), fmt).date()
                        except ValueError:
                            pass
                return d_val

            clean_dob = clean_date(dob)
            clean_join = clean_date(joining_date)

            payload = {
                'first_name': str(first_name).strip() if first_name else '',
                'last_name': str(last_name).strip() if last_name else '',
                'email': str(email).strip() if email else '',
                'phone': str(phone).strip() if phone else '',
                'dob': clean_dob,
                'gender': str(gender).strip().upper() if gender else '',
                'address_line1': str(address).strip() if address else '',
                'city': str(city).strip() if city else '',
                'state': str(state).strip().upper() if state else '',
                'pin_code': str(pin).strip() if pin else '',
                'department': dept.id if dept else None,
                'designation': str(designation).strip() if designation else '',
                'employment_type': str(emp_type).strip().upper() if emp_type else '',
                'joining_date': clean_join,
                'notice_period_days': int(notice_period) if notice_period is not None else 30,
                'bond_period_months': int(bond_period) if bond_period is not None else 0,
                'emergency_contact_name': str(emergency_name).strip() if emergency_name else '',
                'emergency_relationship': str(emergency_rel).strip().upper() if emergency_rel else '',
                'emergency_phone': str(emergency_phone).strip() if emergency_phone else ''
            }

            serializer = EmployeeSerializer(data=payload, context={'request': request})
            if not serializer.is_valid():
                all_errors = {**serializer.errors, **row_errors}
                error_msg = "; ".join([f"{k}: {', '.join(v) if isinstance(v, list) else v}" for k, v in all_errors.items()])
                error_rows.append(list(row) + [error_msg])
                errors_occurred = True
            else:
                if row_errors:
                    error_msg = "; ".join([f"{k}: {v}" for k, v in row_errors.items()])
                    error_rows.append(list(row) + [error_msg])
                    errors_occurred = True
                else:
                    parsed_employees.append(serializer)

        if errors_occurred:
            err_wb = Workbook()
            err_ws = err_wb.active
            err_ws.title = "Failed Rows"
            excel_headers = [
                'First Name', 'Last Name', 'Email', 'Phone', 'DOB', 'Gender', 
                'Address', 'City', 'State', 'PIN', 'Department', 'Designation', 
                'Employment Type', 'Joining Date', 'Notice Period', 'Bond Period', 
                'Emergency Name', 'Emergency Relationship', 'Emergency Phone', 'Error Details'
            ]
            err_ws.append(excel_headers)
            for er_row in error_rows:
                err_ws.append(er_row)

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="import_errors.xlsx"'
            err_wb.save(response)
            return response
        else:
            try:
                with transaction.atomic():
                    for ser in parsed_employees:
                        emp = ser.save()
                        from .tasks import sync_employee_to_bitrix24
                        sync_employee_to_bitrix24.delay(emp.id)
                return Response({
                    'message': f"{len(parsed_employees)} employees imported successfully."
                }, status=status.HTTP_201_CREATED)
            except Exception as ex:
                return Response({'error': f"Failed to save records: {ex}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'], url_path='export-excel')
    def excel_export(self, request):
        queryset = self.get_queryset()
        
        dept_id = request.query_params.get('department')
        emp_type = request.query_params.get('employment_type')
        status_param = request.query_params.get('status')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        if dept_id:
            queryset = queryset.filter(department_id=dept_id)
        if emp_type:
            queryset = queryset.filter(employment_type=emp_type)
        if status_param and status_param != 'All':
            queryset = queryset.filter(status=status_param)
        if from_date:
            queryset = queryset.filter(joining_date__gte=from_date)
        if to_date:
            queryset = queryset.filter(joining_date__lte=to_date)

        import openpyxl
        from openpyxl import Workbook
        from django.http import HttpResponse

        wb = Workbook()
        ws = wb.active
        ws.title = "Employees"

        headers = [
            'Employee ID', 'First Name', 'Last Name', 'Email', 'Phone', 'Alternate Phone',
            'DOB', 'Gender', 'Address Line 1', 'Address Line 2', 'City', 'State', 'PIN Code',
            'Department', 'Designation', 'Employment Type', 'Joining Date', 'Notice Period', 'Bond Period',
            'Emergency Name', 'Emergency Relationship', 'Emergency Phone', 'Status', 'Onboarding Status'
        ]
        ws.append(headers)

        for emp in queryset:
            ws.append([
                emp.emp_id,
                emp.first_name,
                emp.last_name,
                emp.email,
                emp.phone,
                emp.alternate_phone or '',
                emp.dob.strftime('%Y-%m-%d') if emp.dob else '',
                emp.get_gender_display(),
                emp.address_line1,
                emp.address_line2 or '',
                emp.city,
                emp.get_state_display(),
                emp.pin_code,
                emp.department.name if emp.department else '',
                emp.designation,
                emp.get_employment_type_display(),
                emp.joining_date.strftime('%Y-%m-%d') if emp.joining_date else '',
                emp.notice_period_days,
                emp.bond_period_months,
                emp.emergency_contact_name,
                emp.get_emergency_relationship_display(),
                emp.emergency_phone,
                emp.status,
                'Completed' if emp.onboarding_complete else 'Under Onboarding'
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="employees_export.xlsx"'
        wb.save(response)
        return response


class EmployeeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        queryset = EmployeeDocument.objects.all().order_by('-upload_date')
        employee_id = self.request.query_params.get('employee_id')
        if employee_id:
            queryset = queryset.filter(employee_id=employee_id)
        return queryset

    def perform_create(self, serializer):
        doc = serializer.save()
        # Log upload in audit logs
        from audit_logs.signals import log_action
        log_action(self.request.user, "UPLOAD", doc, f"Uploaded document '{doc.get_doc_type_display()}' ({doc.original_filename}) for employee {doc.employee.emp_id}.")
        # Sync to Bitrix24 timeline
        from .tasks import attach_document_to_bitrix24_timeline
        attach_document_to_bitrix24_timeline.delay(doc.id)


DEFAULT_TEMPLATES = [
    {
        'name': 'OFFER_LETTER',
        'title': 'Default Offer Letter Template',
        'html_content': """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Offer Letter</title>
    <style>
        @page {
            size: A4;
            margin: 20mm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-family: Arial, sans-serif;
                font-size: 9pt;
                color: #555;
            }
        }
        body {
            font-family: Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #333;
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #7c3aed;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        .company-name {
            font-size: 20pt;
            font-weight: bold;
            color: #7c3aed;
        }
        .company-sub {
            font-size: 10pt;
            color: #555;
        }
        .date {
            text-align: right;
            margin-bottom: 20px;
        }
        .subject {
            font-weight: bold;
            text-decoration: underline;
            margin-bottom: 25px;
        }
        .salutation {
            margin-bottom: 15px;
        }
        .content {
            margin-bottom: 30px;
        }
        .details-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .details-table td {
            padding: 8px;
            border: 1px solid #ddd;
        }
        .details-table td.label {
            font-weight: bold;
            background-color: #f9f9f9;
            width: 30%;
        }
        .signature-section {
            margin-top: 50px;
            page-break-inside: avoid;
        }
        .signature-line {
            width: 200px;
            border-top: 1px solid #333;
            margin-top: 40px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-name">{{ company_name }}</div>
        <div class="company-sub">HR Division • Secure Enterprise Operations</div>
    </div>
    
    <div class="date">Date: {{ date }}</div>
    
    <div class="salutation">Dear {{ name }},</div>
    
    <div class="subject">Subject: Offer of Employment</div>
    
    <div class="content">
        <p>With reference to your application and subsequent interview, we are pleased to offer you the position of <strong>{{ designation }}</strong> in the department at <strong>{{ company_name }}</strong>.</p>
        
        <p>Your employment details are outlined below:</p>
        
        <table class="details-table">
            <tr>
                <td class="label">Employee ID</td>
                <td>{{ employee.emp_id }}</td>
            </tr>
            <tr>
                <td class="label">Designation</td>
                <td>{{ designation }}</td>
            </tr>
            <tr>
                <td class="label">Joining Date</td>
                <td>{{ joining_date }}</td>
            </tr>
            <tr>
                <td class="label">Notice Period</td>
                <td>{{ employee.notice_period_days }} Days</td>
            </tr>
            {% if bond_period > 0 %}
            <tr>
                <td class="label">Service Bond</td>
                <td>{{ bond_period }} Months</td>
            </tr>
            {% endif %}
        </table>
        
        <p>This offer is subject to the verification of your references and background checks, as well as the submission of required onboarding documents (Aadhaar, PAN, certificates).</p>
        
        <div style="page-break-before: always;"></div>
        <div class="header">
            <div class="company-name">{{ company_name }}</div>
            <div class="company-sub">HR Division • Annexure A: CTC Salary Structure</div>
        </div>
        <p>Salary Structure details for <strong>{{ name }}</strong>:</p>
        <table class="details-table">
            <thead>
                <tr style="background-color: #7c3aed; color: white; font-weight: bold;">
                    <td>Earnings Component</td>
                    <td>Monthly (Rs.)</td>
                    <td>Deductions Component</td>
                    <td>Monthly (Rs.)</td>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="label">Basic Salary</td>
                    <td>{{ basic }}</td>
                    <td class="label">Provident Fund (PF)</td>
                    <td>{{ pf }}</td>
                </tr>
                <tr>
                    <td class="label">House Rent Allowance (HRA)</td>
                    <td>{{ hra }}</td>
                    <td class="label">Professional Tax (PT)</td>
                    <td>{{ professional_tax }}</td>
                </tr>
                <tr>
                    <td class="label">Conveyance Allowance</td>
                    <td>{{ conveyance }}</td>
                    <td class="label">TDS (Income Tax)</td>
                    <td>{{ tds }}</td>
                </tr>
                <tr>
                    <td class="label">Medical Allowance</td>
                    <td>{{ medical }}</td>
                    <td class="label">Other Deductions</td>
                    <td>0.00</td>
                </tr>
                <tr>
                    <td class="label">Special Allowance</td>
                    <td>{{ special }}</td>
                    <td></td>
                    <td></td>
                </tr>
                {% if monthly_bonus > 0 %}
                <tr>
                    <td class="label">Monthly Bonus</td>
                    <td>{{ monthly_bonus }}</td>
                    <td></td>
                    <td></td>
                </tr>
                {% endif %}
                <tr style="font-weight: bold; background-color: #f9f9f9;">
                    <td>Gross Salary (A)</td>
                    <td>{{ gross_salary }}</td>
                    <td>Total Deductions (B)</td>
                    <td>{{ total_deductions }}</td>
                </tr>
                <tr style="font-weight: bold; background-color: #f3e8ff; color: #7c3aed;">
                    <td colspan="2">Net Take-Home Salary (A - B)</td>
                    <td colspan="2">Rs. {{ net_salary }} / month</td>
                </tr>
            </tbody>
        </table>
        
        <p>Please sign and return the duplicate copy of this letter as a token of your acceptance of this offer.</p>
    </div>
    
    <div class="signature-section">
        <p>For <strong>{{ company_name }}</strong>,</p>
        <div class="signature-line">
            <strong>{{ signatory_name }}</strong><br>
            {{ signatory_designation }}
        </div>
    </div>
</body>
</html>"""
    },
    {
        'name': 'APPOINTMENT_LETTER',
        'title': 'Default Appointment Letter Template',
        'html_content': """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Appointment Letter</title>
    <style>
        @page {
            size: A4;
            margin: 15mm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-family: Arial, sans-serif;
                font-size: 8pt;
                color: #555;
            }
        }
        body {
            font-family: Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: #333;
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #7c3aed;
            padding-bottom: 8px;
            margin-bottom: 20px;
        }
        .company-name {
            font-size: 18pt;
            font-weight: bold;
            color: #7c3aed;
        }
        .company-sub {
            font-size: 9pt;
            color: #555;
        }
        .date {
            text-align: right;
            margin-bottom: 15px;
        }
        .salutation {
            margin-bottom: 12px;
            font-weight: 500;
        }
        .content {
            margin-bottom: 25px;
        }
        .details-table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 9pt;
        }
        .details-table td {
            padding: 6px 10px;
            border: 1px solid #ddd;
        }
        .details-table td.label {
            font-weight: bold;
            background-color: #f9f9f9;
            width: 35%;
        }
        .signature-row {
            margin-top: 35px;
            display: table;
            width: 100%;
            page-break-inside: avoid;
        }
        .signature-col {
            display: table-cell;
            width: 25%;
            vertical-align: bottom;
            text-align: left;
        }
        .signature-line {
            border-top: 1px dashed #333;
            width: 130px;
            margin-top: 30px;
            padding-top: 5px;
            font-size: 8.5pt;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="company-name">{{ company_name }}</div>
        <div class="company-sub">HR Division • Letter of Appointment</div>
    </div>
    
    <div class="date">Date: {{ date }}</div>
    
    <div class="salutation">Dear {{ name }},</div>
    
    <div class="content">
        <p>We are pleased to offer you a position of <strong>{{ designation }}</strong> at <strong>{{ company_name }}</strong>. (Hereinafter to be referred as a “Company”), commencing from <strong>{{ joining_date }}</strong> or another mutually agreed upon date and you will report to Mr. Prince Parbhakar, The Project Manager at {{ company_name }}.</p>

        <p>Please note that your employment with the company shall be governed by the policies, rules and regulations of the company as specifically mentioned herein by way of references and in force or as amended or altered time to time/ duly notified. The terms and conditions mentioned below:</p>

        <p><strong>1. Remuneration:</strong> The Company is pleased to offer you INR {{ ctc }} CTC per month. Your compensation is confidential and should not be disclosed or discussed with any other employee of the organization. It may be adjusted periodically in accordance with the company’s prevailing employee remuneration guidelines.</p>
        
        <p><strong>2. Probation:</strong> You will be on probation for 3 months from the date of joining the company. The company retains the right to terminate the employment of any employee immediately for just cause, without prior notice or compensation in lieu of notice. If the termination is for reasons other than just cause, the company will comply with the legal requirement to provide the minimum notice period stipulated by law.</p>
        
        <p><strong>3. General Policy:</strong> This role required a full time commitment, Monday to Friday, with a total of 9 hours per day, incorporating a 45 minutes lunch break from 1:30PM to 2:15PM.</p>
        
        <p><strong>4. Leave Policy:</strong><br>
        A. During the probation period, employees are not eligible for paid leave.<br>
        B. As a regular employee, you may take up to 1 full day leave and 1 half day or 2 short leaves per month, subject to prior approval and adherence to company policies.<br>
        C. Sandwich:-<br>
        1. If an employee takes leave on Friday and Monday then it will be counted as a sandwich leave and there is no relaxation in this situation.<br>
        2. If the employee leaves on Friday, Saturday, Sunday OR Saturday, Sunday, Monday then it will also be considered as a sandwich leave but we will give exemption once in every 3 months.<br>
        D. Carried forward leaves are limited to one financial year and Six leaves encashment will be allowed at the end of the year.</p>

        <p><strong>5. Non-Disclosure of Information:</strong> As a part of your employment, you agree to keep all company information confidential, including business strategies, and financial data. Unauthorized disclosure may lead to disciplinary action, including termination and potential legal consequences.</p>
        
        <p><strong>6. Proprietary Information and Inventions Agreement:</strong> As a condition of your employment, you will be required to sign the Company’s Proprietary Information and Inventions Agreement.</p>

        <p><strong>7. Tax Matters:</strong><br>
        ● Tax Advice: You are encouraged to obtain your own tax advice regarding your compensation from the Company. You agree that the Company does not have a duty to design its compensation policies in a manner that minimizes your tax liabilities, and you will not make any claim against the Company or its Board of Directors related to tax liabilities arising from your compensation.<br>
        ● Interpretation, Amendment and Enforcement: This letter agreement supersedes and replaces any prior agreements, representations or understandings (whether written, oral, implied or otherwise) between you and the Company and constitutes the complete agreement between you and the Company regarding the subject matter set forth herein. This letter agreement may not be amended or modified, except by an express written agreement signed by both you and a duly authorized officer of the Company. You may indicate your agreement with these terms and accept this offer by signing and dating this agreement or before ({{ joining_date }}). Upon your acceptance of this employment offer, {{ company_name }} will provide you with the necessary paperwork and instructions.</p>
        
        <p>Sincerely,</p>
    </div>
    
    <div class="signature-row" style="margin-top: 15px;">
        <div class="signature-col">
            <div class="signature-line">Applicant (Sign)</div>
        </div>
        <div class="signature-col">
            <div class="signature-line">Company Rep (Sign)</div>
        </div>
        <div class="signature-col">
            <div class="signature-line">CTO</div>
        </div>
        <div class="signature-col">
            <div class="signature-line">HR Department</div>
        </div>
    </div>

    <div style="page-break-before: always;"></div>
    <div class="header">
        <div class="company-name">{{ company_name }}</div>
        <div class="company-sub">HR Division • Annexure A: CTC Salary Breakup</div>
    </div>
    
    <h4 style="margin: 0; font-size:12px; font-weight: 700;">SALARY BREAKUP DETAILED PLAN</h4>
    <table class="details-table">
        <tbody>
            <tr>
                <td class="label">CTC (Cost to Company)</td>
                <td style="font-weight: bold;">INR {{ ctc }} / month</td>
            </tr>
            <tr>
                <td class="label">ESI - Employer Share</td>
                <td>INR {{ esi_employer }}</td>
            </tr>
            <tr>
                <td class="label">PF - Employer Share</td>
                <td>INR {{ pf_employer }}</td>
            </tr>
            <tr style="font-weight: bold; background-color: #f1f5f9;">
                <td class="label">Gross Salary</td>
                <td>INR {{ gross_salary }}</td>
            </tr>
            <tr>
                <td class="label">PF - Employee Share</td>
                <td>INR {{ pf_employee }}</td>
            </tr>
            <tr>
                <td class="label">ESI - Employee Share</td>
                <td>INR {{ esi_employee }}</td>
            </tr>
            <tr>
                <td class="label">Labour Welfare Fund (LWF)</td>
                <td>INR {{ lwf }}</td>
            </tr>
            <tr>
                <td class="label">Professional Tax (PT)</td>
                <td>INR {{ professional_tax }}</td>
            </tr>
            <tr style="font-weight: bold; background-color: #ecfdf5; color: #10b981;">
                <td class="label">Net In-Hand Salary</td>
                <td>INR {{ in_hand }} / month</td>
            </tr>
        </tbody>
    </table>

    <div class="signature-row" style="margin-top: 40px;">
        <div class="signature-col">
            <div class="signature-line">Applicant (Sign)</div>
        </div>
        <div class="signature-col">
            <div class="signature-line">Company Rep (Sign)</div>
        </div>
        <div class="signature-col">
            <div class="signature-line">CTO</div>
        </div>
        <div class="signature-col">
            <div class="signature-line">HR Department</div>
        </div>
    </div>
</body>
</html>"""
    },
    {
        'name': 'BOND_LETTER',
        'title': 'Default Employment Bond Template',
        'html_content': """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Employment Bond Agreement</title>
    <style>
        @page {
            size: A4;
            margin: 20mm;
            @bottom-right {
                content: "Page " counter(page) " of " counter(pages);
                font-family: 'Times New Roman', Times, serif;
                font-size: 9pt;
                color: #000;
            }
        }
        body {
            font-family: 'Times New Roman', Times, serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #000;
            background-color: #fff;
        }
        .title {
            text-align: center;
            font-size: 14pt;
            font-weight: bold;
            margin: 20px 0 30px 0;
            text-transform: uppercase;
            text-decoration: underline;
        }
        .content {
            margin-bottom: 30px;
            text-align: justify;
        }
        .content p {
            margin-bottom: 15px;
            text-indent: 0px;
        }
        .signature-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 30px;
            page-break-inside: avoid;
        }
        .signature-table td {
            padding: 8px 0;
            font-size: 11pt;
            vertical-align: bottom;
        }
    </style>
</head>
<body>
    <div class="title">Employment Bond Letter</div>
    
    <div class="content">
        <p>THIS AGREEMENT made as of the <strong>{{ date }}</strong>, between <strong>{{ company_name }}</strong> and <strong>{{ employee_name }}</strong> and having its principal place of business at {{ company_address }}. WHEREAS the Employer desires to obtain the benefit of the services of the Employee, and the Employee desires to render such services on the terms and conditions set forth.</p>
        
        <p>IN CONSIDERATION of the promises and other good and valuable consideration (the sufficiency and receipt of which are hereby acknowledged) the parties agree as follows:-</p>
        
        <p><strong>1. Employment:</strong><br>
        The Employee agrees that he will at all times faithfully, industriously, and to the best of his skill, ability, experience and talents, perform all of the duties required of his position. In carrying out these duties and responsibilities, the Employee shall comply with all Employer policies, procedures, rules and regulations, both written and oral, as are announced by the Employer from time to time. It is also understood and agreed to by the Employee that his assignment, duties and responsibilities and reporting arrangements may be changed by the Employer in its sole discretion without causing termination of this agreement.</p>
        
        <p><strong>2. Position Title:</strong><br>
        As a {{ designation }} the Employee is required to perform the duties and undertake responsibilities in a professional manner which may be assigned by the employer. This Agreement shall be defined as, the employee will not leave the position at least {{ bond_period }} months. In case they broke this agreement and left in between without notice period or any serious issues they have to give back two months’ salary to the company.</p>
        
        <p><strong>3. Compensation:</strong><br>
        (a) As full compensation for all services provided the employee shall be paid at the given rate. Such payments shall be subject to such normal statutory deductions by the Employer.<br>
        (b) The salary mentioned in your offer letter.<br>
        (c) All reasonable expenses arising out of employment shall be reimbursed assuming the same have been authorized prior to being incurred and with the provision of appropriate receipts.</p>
        
        <p><strong>4. Probation Period:</strong><br>
        It is understood and agreed that the {{ probation_period }} months of employment shall constitute a probationary period during which period the Employer may, in its absolute discretion, terminate the Employee's employment, for any reason without notice or cause. If your services are found to be satisfactory during the probationary period, you will be confirmed in the present position and thereafter your services can be terminated on {{ notice_period }} days of notice on either side.</p>
        
        <p><strong>5. Performance Reviews:</strong><br>
        The Employee will be provided with a written performance appraisal at least once per year and said appraisal will be reviewed by the manager at which time all aspects of the assessment can be fully discussed.</p>
        
        <p><strong>6. Termination and Resignation:</strong><br>
        (a) The Employee shall not terminate this agreement and his employment during the time of the bond period. Employees have to give two months' prior written notice to the Employer and have to pay 2 months' salary to the company if the Employee leaves the company before the bond period.<br>
        (b) The Employer may terminate this Agreement and the Employee’s employment at any time, without notice or payment in lieu of notice, for sufficient cause.<br>
        (c) If the employee will not serve given Notice and leave the organization in that case company will not provide any Experience letter and employee has to give back two months’ salary to company.<br>
        (d) The Government Exams, Female marriage, planning to go abroad for further future in that case the company will relieve the employee after receiving official documents.<br>
        (d) The employee agrees to return any property of the company at the time of termination.</p>
        
        <p><strong>7. Non- Competition:</strong><br>
        (1) It is further acknowledged and agreed that following termination of the employee’s employment with {{ company_name }} for any reason the employee shall not hire or attempt to hire any current employees of {{ company_name }}.<br>
        (2) It is further acknowledged and agreed that following termination of the employee’s employment with {{ company_name }} for any reason the employee shall not solicit business from current clients or existing clients, in that case the company will take legal action against them.</p>
        
        <p><strong>8. Pay and Incentive Policy:</strong><br>
        Pay shall be given by the medium of the bank on the 10th of every month. Incentives are subjected to the performance of the employee.</p>
        
        <p><strong>9. Holiday/ Vacation/ Leave:</strong><br>
        The list of holidays will be displayed and the information shall be conveyed to the employees. The employees are given Eighteen leaves per year i.e. one full day leave per month and one half day leave or two short days leaves per month. If any employee is not taking any leave in a month that leave is going to be added in the next month and any employee can take a maximum of two carry forwarded leaves in a month otherwise there will be salary deduction. If any employee takes leave before or after week offs and holidays then it will be counted as a sandwich.</p>
        
        <p><strong>10. Entire Agreement:</strong><br>
        This agreement contains the entire agreement between the parties, superseding in all respects any and all prior oral or written agreements or understandings pertaining to the employment of the Employee by the Employer and shall be amended or modified only by written instrument signed by both of the parties here to.</p>
        
        <p><strong>11. IN WITNESS WHEREOF:</strong><br>
        The Employer has caused this agreement to be executed by its duly authorized officers and the Employee has set his hand as of the date first above written.</p>
    </div>
    
    <div style="margin-top: 45px; page-break-inside: avoid;">
        <p>SIGNED, SEALED AND DELIVERED in the presence of:</p>
        <table class="signature-table">
            <tr>
                <td style="width: 45%;">[Name of employee] _______________________</td>
                <td style="width: 55%;">{{ employee_name }}</td>
            </tr>
            <tr>
                <td style="width: 45%;">[Signature of Employee] __________________</td>
                <td style="width: 55%;">___________________________________________</td>
            </tr>
            <tr>
                <td style="width: 45%;">[Name of Employer Rep] __________________</td>
                <td style="width: 55%;">{{ signatory_name }}</td>
            </tr>
            <tr>
                <td style="width: 45%;">[Signature of Employer Rep] ______________</td>
                <td style="width: 55%;">___________________________________________</td>
            </tr>
        </table>
    </div>
</body>
</html>"""
    }
]


class LetterTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = LetterTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Automatically seed templates if they do not exist
        if LetterTemplate.objects.count() == 0:
            for t in DEFAULT_TEMPLATES:
                LetterTemplate.objects.create(**t)
        else:
            # Overwrite default BOND_LETTER to align layout instantly
            for t in DEFAULT_TEMPLATES:
                obj = LetterTemplate.objects.filter(name=t['name']).first()
                if obj and t['name'] == 'BOND_LETTER':
                    obj.html_content = t['html_content']
                    obj.save()
        return LetterTemplate.objects.all().order_by('name')

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user
        is_admin = user.is_superuser or (user.role and user.role.code == 'ADMIN')
        
        if not is_admin:
            user_perms = list(user.role.permissions.values_list('codename', flat=True)) if user.role else []
            has_manage_perm = 'onboarding.manage_templates' in user_perms
            is_hr = user.role and user.role.code == 'HR'
            
            if not has_manage_perm:
                if not is_hr or not obj.allow_hr_edit:
                    raise PermissionDenied("You do not have permission to edit this template.")
                
        return super().update(request, *args, **kwargs)

