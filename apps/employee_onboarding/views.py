from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from roles.permissions import HasModelPermission
from rules import ROLE_ADMIN
from .models import Department, EmployeeDocument, LetterTemplate
from common.bitrix_client import BitrixClient, BitrixEmployeeMock
from .serializers import DepartmentSerializer, EmployeeSerializer, EmployeeDocumentSerializer, LetterTemplateSerializer
from .services import generate_offer_letter, generate_appointment_letter, generate_bond_letter
import os
import mimetypes
from django.http import FileResponse, Http404
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

class QueryParamJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Check header first using parent implementation
        header_auth = super().authenticate(request)
        if header_auth is not None:
            return header_auth
            
        # Check query parameter
        raw_token = request.query_params.get('token')
        if not raw_token:
            return None
            
        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except Exception:
            raise AuthenticationFailed("Invalid or expired token.")

class SecureDocumentServeView(APIView):
    authentication_classes = [QueryParamJWTAuthentication]
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

from rest_framework.pagination import PageNumberPagination

class EmployeePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class EmployeeViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeSerializer
    permission_classes = [HasModelPermission]
    pagination_class = EmployeePagination

    def get_queryset(self):
        users = BitrixClient.get_all_users()
        mocks = [BitrixEmployeeMock(u) for u in users]
        return mocks

    def get_object(self):
        pk = self.kwargs.get('pk')
        user = BitrixClient.get_user_detail(pk)
        if not user:
            raise Http404("Employee not found in Bitrix24.")
        return BitrixEmployeeMock(user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # 1. Search query
        search_query = request.query_params.get('search')
        if search_query:
            search_query = search_query.lower()
            queryset = [
                u for u in queryset 
                if search_query in u.name.lower() or search_query in u.email.lower() or search_query in u.emp_id.lower()
            ]

        # 2. Department filter
        dept_id = request.query_params.get('department')
        if dept_id:
            queryset = [
                u for u in queryset
                if str(u.department) == str(dept_id) or str(dept_id) in [str(d) for d in getattr(u, 'UF_DEPARTMENT', [])]
            ]

        # 3. Employment Type filter
        emp_type = request.query_params.get('employment_type')
        if emp_type:
            queryset = [
                u for u in queryset
                if u.employment_type.upper().replace(' ', '_').replace('-', '_') == emp_type.upper()
            ]

        # 4. Date range filters
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        if from_date:
            queryset = [u for u in queryset if str(u.joining_date) >= str(from_date)]
        if to_date:
            queryset = [u for u in queryset if str(u.joining_date) <= str(to_date)]
            
        # 5. List type split logic
        list_type = request.query_params.get('type')
        import datetime
        today = datetime.date.today()
        day_14_ago = today - datetime.timedelta(days=14)
        
        filtered_users = []
        for u in queryset:
            if list_type == 'onboarding':
                if u.joining_date > day_14_ago:
                    # Filter out exited users from onboarding list
                    if u.status != 'Exited':
                        filtered_users.append(u)
            elif list_type == 'all':
                # Filter out exited users from active directory
                if u.status != 'Exited':
                    filtered_users.append(u)
            elif list_type == 'offboarding':
                if u.status == 'Exited' or getattr(u, 'exit_request_id', None) is not None:
                    filtered_users.append(u)
            elif list_type == 'dismissed':
                if u.status == 'Exited' or getattr(u, 'is_deleted', False) is True:
                    filtered_users.append(u)
            else:
                filtered_users.append(u)

        # 6. Sort ordering
        sort_by = request.query_params.get('sort')
        if sort_by == 'name':
            filtered_users.sort(key=lambda u: u.name.lower())
        elif sort_by == 'date':
            filtered_users.sort(key=lambda u: str(u.joining_date))
        elif sort_by == 'id':
            filtered_users.sort(key=lambda u: u.emp_id.lower())
                 
        # Pagination
        no_pagination = request.query_params.get('no_pagination') == 'true'
        if not no_pagination:
            page = self.paginate_queryset(filtered_users)
            if page is not None:
                serializer = self.get_serializer([u._data for u in page], many=True)
                return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer([u._data for u in filtered_users], many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        employee = self.get_object()
        serializer = self.get_serializer(employee._data)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        data = request.data
        webhook = BitrixClient.get_webhook_url()
        create_url = f"{webhook}/crm.contact.add"
        
        payload = {
            'fields': {
                'NAME': data.get('first_name'),
                'LAST_NAME': data.get('last_name'),
                'EMAIL': [{'VALUE': data.get('email'), 'VALUE_TYPE': 'WORK'}],
                'PHONE': [{'VALUE': data.get('phone'), 'VALUE_TYPE': 'WORK'}],
                'POST': data.get('designation'),
                'UF_ONBOARDING_STATUS': 'Pending',
                'UF_CRM_ONBOARDING_STATUS': 'Pending'
            }
        }
        
        try:
            import requests
            res = requests.post(create_url, json=payload, timeout=10)
            if res.ok:
                contact_id = str(res.json().get('result'))
                BitrixClient.get_all_users(force_refresh=True)
                mock_user = BitrixClient.get_user_detail(contact_id)
                # Write to audit logs
                from audit_logs.signals import log_action
                log_action(request.user, "CREATE", None, f"Created Bitrix24 employee contact {data.get('first_name')} {data.get('last_name')} (ID: {contact_id}).")
                return Response(mock_user, status=status.HTTP_201_CREATED)
            else:
                return Response({'error': f"Bitrix24 API Error: {res.text}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        data = request.data
        webhook = BitrixClient.get_webhook_url()
        update_url = f"{webhook}/crm.contact.update"
        
        payload = {
            'id': pk,
            'fields': {
                'NAME': data.get('first_name'),
                'LAST_NAME': data.get('last_name'),
                'EMAIL': [{'VALUE': data.get('email'), 'VALUE_TYPE': 'WORK'}],
                'PHONE': [{'VALUE': data.get('phone'), 'VALUE_TYPE': 'WORK'}],
                'POST': data.get('designation'),
            }
        }
        
        try:
            import requests
            res = requests.post(update_url, json=payload, timeout=10)
            if res.ok:
                BitrixClient.get_all_users(force_refresh=True)
                user = BitrixClient.get_user_detail(pk)
                # Log action
                from audit_logs.signals import log_action
                log_action(request.user, "UPDATE", None, f"Updated Bitrix24 employee contact (ID: {pk}).")
                return Response(user)
            else:
                return Response({'error': f"Bitrix24 API Error: {res.text}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None, *args, **kwargs):
        return self.update(request, pk, *args, **kwargs)

    def destroy(self, request, pk=None, *args, **kwargs):
        webhook = BitrixClient.get_webhook_url()
        delete_url = f"{webhook}/crm.contact.delete"
        try:
            import requests
            requests.post(delete_url, json={'id': pk}, timeout=10)
        except Exception:
            pass
        BitrixClient.get_all_users(force_refresh=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['POST'], url_path='manual-graduate')
    def manual_graduate(self, request, pk=None):
        webhook = BitrixClient.get_webhook_url()
        update_url = f"{webhook}/crm.contact.update"
        payload = {
            'id': pk,
            'fields': {
                'UF_ONBOARDING_STATUS': 'Completed',
                'UF_CRM_ONBOARDING_STATUS': 'Completed'
            }
        }
        try:
            import requests
            requests.post(update_url, json=payload, timeout=10)
        except Exception:
            pass
        BitrixClient.get_all_users(force_refresh=True)
        return Response({'message': 'Employee onboarding completed successfully.'})

    @action(detail=True, methods=['POST'], url_path='retry-bitrix-sync')
    def retry_bitrix_sync(self, request, pk=None):
        return Response({'message': 'Project is running in Pure API mode. Sync is always active.'})

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
        return Response({
            'message': 'Direct excel import is disabled in Pure API mode. Please add team members in Bitrix24 directly.'
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'], url_path='export-excel')
    def excel_export(self, request):
        queryset = self.get_queryset()
        
        dept_id = request.query_params.get('department')
        emp_type = request.query_params.get('employment_type')
        status_param = request.query_params.get('status')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        
        if emp_type:
            queryset = [emp for emp in queryset if emp.employment_type == emp_type]
        if status_param and status_param != 'All':
            queryset = [emp for emp in queryset if emp.status == status_param]
        if from_date:
            try:
                import datetime
                from_dt = datetime.datetime.strptime(from_date, '%Y-%m-%d').date()
                queryset = [emp for emp in queryset if emp.joining_date >= from_dt]
            except ValueError:
                pass
        if to_date:
            try:
                import datetime
                to_dt = datetime.datetime.strptime(to_date, '%Y-%m-%d').date()
                queryset = [emp for emp in queryset if emp.joining_date <= to_dt]
            except ValueError:
                pass

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
                emp.department_name,
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
                    
        # Automatically seed exit templates if they do not exist
        exit_templates_seeding = [
            ('RELIEVING_LETTER', 'Relieving Letter Template', 'pdf_relieving_letter.html'),
            ('EXPERIENCE_LETTER', 'Experience Letter Template', 'pdf_experience_letter.html'),
            ('NOTICE_LETTER', 'Notice Period Letter Template', 'pdf_notice_letter.html'),
            ('NOC_LETTER', 'NOC Letter Template', 'pdf_noc_letter.html'),
            ('FF_SETTLEMENT_LETTER', 'F&F Settlement Letter Template', 'pdf_ff_settlement_letter.html'),
            ('FF_SALARY_SLIP', 'Final Month Payslip Template', 'pdf_ff_salary_slip.html'),
        ]
        
        for name, title, filename in exit_templates_seeding:
            if not LetterTemplate.objects.filter(name=name).exists():
                try:
                    file_path = os.path.join(settings.BASE_DIR, 'templates', 'exit', filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    LetterTemplate.objects.create(
                        name=name,
                        title=title,
                        html_content=html_content,
                        allow_hr_edit=False
                    )
                except Exception as e:
                    pass
                    
        return LetterTemplate.objects.all().order_by('name')


    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user
        is_admin = user.is_superuser or (user.role and user.role.code == 'ADMIN')
        
        if not is_admin:
            user_perms = list(user.role.permissions.values_list('codename', flat=True)) if user.role else []
            is_hr = user.role and user.role.code == 'HR'
            
            is_exit_template = obj.name in [
                'RELIEVING_LETTER', 'EXPERIENCE_LETTER', 'NOTICE_LETTER', 
                'NOC_LETTER', 'FF_SETTLEMENT_LETTER', 'FF_SALARY_SLIP'
            ]
            
            if is_exit_template:
                has_manage_perm = 'exit.manage_templates' in user_perms
                if not has_manage_perm:
                    raise PermissionDenied("You do not have permission to edit this exit template.")
            else:
                has_manage_perm = 'onboarding.manage_templates' in user_perms
                if not has_manage_perm:
                    if not is_hr or not obj.allow_hr_edit:
                        raise PermissionDenied("You do not have permission to edit this template.")
                
        return super().update(request, *args, **kwargs)


