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
        
        # Decorate mock users with local exit_request_id if an exit request exists
        try:
            from exit_formality.models import ExitRequest
            exit_requests = ExitRequest.objects.all().order_by('initiated_at')
            exit_requests_map = {str(er.bitrix_user_id): er for er in exit_requests}
            for u in mocks:
                bitrix_id_str = str(u.id)
                if bitrix_id_str in exit_requests_map:
                    er = exit_requests_map[bitrix_id_str]
                    u.exit_request_id = er.id
                    u._data['exit_request_id'] = er.id
                    u.exit_request_status = er.status
                    u._data['exit_request_status'] = er.status
        except Exception:
            pass
            
        return mocks

    def get_object(self):
        pk = self.kwargs.get('pk')
        user = BitrixClient.get_user_detail(pk)
        if not user:
            raise Http404("Employee not found in Bitrix24.")
        mock = BitrixEmployeeMock(user)
        
        # Decorate mock user with local exit_request_id if an exit request exists
        try:
            from exit_formality.models import ExitRequest
            exit_req = ExitRequest.objects.filter(bitrix_user_id=str(mock.id)).order_by('-initiated_at').first()
            if exit_req:
                mock.exit_request_id = exit_req.id
                mock._data['exit_request_id'] = exit_req.id
                mock.exit_request_status = exit_req.status
                mock._data['exit_request_status'] = exit_req.status
        except Exception:
            pass
            
        return mock

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
                is_exited = u.status == 'Exited'
                has_pending_exit = getattr(u, 'exit_request_status', None) == 'PENDING'
                
                if has_pending_exit and not is_exited:
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
        
        gender_code = 'M'
        if data.get('gender') == 'FEMALE':
            gender_code = 'F'
        elif data.get('gender') == 'OTHER':
            gender_code = 'O'

        dept_list = [1]
        if data.get('department'):
            try:
                dept_list = [int(data.get('department'))]
            except (ValueError, TypeError):
                pass

        user_payload = {
            'EMAIL': data.get('work_email') or data.get('email'),
            'NAME': data.get('first_name'),
            'LAST_NAME': data.get('last_name'),
            'PERSONAL_MOBILE': data.get('phone'),
            'WORK_POSITION': data.get('designation'),
            'UF_DEPARTMENT': dept_list,
            'PERSONAL_BIRTHDAY': data.get('dob') or '',
            'PERSONAL_GENDER': gender_code,
            'UF_PERSONAL_EMAIL': data.get('personal_email'),
            'PERSONAL_MAILBOX': data.get('personal_email')
        }
        
        try:
            import requests
            # Attempt to create as user profile first
            res = requests.post(f"{webhook}/user.add.json", json=user_payload, timeout=10)
            
            # Fallback to CRM contact creation if user scope fails or fails otherwise
            if not res.ok:
                emails = []
                email_val = data.get('work_email') or data.get('email')
                if email_val:
                    emails.append({'VALUE': email_val, 'VALUE_TYPE': 'WORK'})
                if data.get('personal_email'):
                    emails.append({'VALUE': data.get('personal_email'), 'VALUE_TYPE': 'HOME'})
                    
                crm_payload = {
                    'fields': {
                        'NAME': data.get('first_name'),
                        'LAST_NAME': data.get('last_name'),
                        'EMAIL': emails,
                        'PHONE': [{'VALUE': data.get('phone'), 'VALUE_TYPE': 'WORK'}],
                        'POST': data.get('designation'),
                        'UF_ONBOARDING_STATUS': 'Pending',
                        'UF_CRM_ONBOARDING_STATUS': 'Pending',
                        'UF_PERSONAL_EMAIL': data.get('personal_email'),
                        'PERSONAL_MAILBOX': data.get('personal_email')
                    }
                }
                res = requests.post(f"{webhook}/crm.contact.add", json=crm_payload, timeout=10)
                
            if res.ok:
                contact_id = str(res.json().get('result'))
                BitrixClient.get_all_users(force_refresh=True)
                mock_user = BitrixClient.get_user_detail(contact_id)
                
                # Log success in BitrixSyncLog
                try:
                    from notifications.models import BitrixSyncLog
                    BitrixSyncLog.objects.create(
                        employee_id=contact_id,
                        employee_name=mock_user.get('name') if mock_user else f"{data.get('first_name')} {data.get('last_name')}".strip(),
                        action_type='Contact Create',
                        status='SUCCESS',
                        retry_count=0
                    )
                except Exception:
                    pass

                # Trigger welcome email task asynchronously
                try:
                    import logging
                    logger = logging.getLogger(__name__)
                    from .tasks import send_onboarding_welcome_email
                    send_onboarding_welcome_email.delay(mock_user)
                except Exception as mail_err:
                    import logging
                    logging.getLogger(__name__).error(f"Failed to queue welcome email task: {mail_err}")
                
                # Trigger Admin Notification (Trigger 1)
                try:
                    from notifications.models import Notification
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    admins = User.objects.filter(role__code='ADMIN')
                    
                    hr_name = request.user.username
                    if request.user.first_name or request.user.last_name:
                        hr_name = f"{request.user.first_name} {request.user.last_name}".strip()
                    
                    notif_msg = f"New employee added – {mock_user.get('name')} ({mock_user.get('emp_id')}) by HR {hr_name}"
                    for admin in admins:
                        if admin != request.user:
                            Notification.objects.create(
                                recipient=admin,
                                notif_type='INFO',
                                message=notif_msg,
                                link=f"/employees/{mock_user.get('id')}/"
                            )
                except Exception as notif_err:
                    logging.getLogger(__name__).error(f"Failed to trigger Trigger 1 notification: {notif_err}")

                # Write to audit logs
                from audit_logs.signals import log_action
                if request.user.is_authenticated:
                    log_action(request.user, "CREATE", None, f"Created Bitrix24 employee contact {data.get('first_name')} {data.get('last_name')} (ID: {contact_id}).")
                return Response(mock_user, status=status.HTTP_201_CREATED)
            else:
                # Log failure in BitrixSyncLog (Trigger 24)
                emp_name = f"{data.get('first_name')} {data.get('last_name')}".strip()
                try:
                    from notifications.models import BitrixSyncLog, Notification
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    BitrixSyncLog.objects.create(
                        employee_name=emp_name,
                        action_type='Contact Create',
                        status='FAILED',
                        retry_count=0,
                        error_message=res.text
                    )
                    
                    # Notify Admin (Trigger 24)
                    admins = User.objects.filter(role__code='ADMIN')
                    notif_msg = f"Bitrix24 sync failed for {emp_name} (Contact Create). Retry available."
                    for admin in admins:
                        Notification.objects.create(
                            recipient=admin,
                            notif_type='ERROR',
                            message=notif_msg,
                            link="/admin/bitrix/sync-log/"
                        )
                except Exception:
                    pass

                return Response({'error': f"Bitrix24 API Error: {res.text}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    def update(self, request, pk=None, *args, **kwargs):
        data = request.data
        webhook = BitrixClient.get_webhook_url()
        
        gender_code = 'M'
        if data.get('gender') == 'FEMALE':
            gender_code = 'F'
        elif data.get('gender') == 'OTHER':
            gender_code = 'O'
            
        payload = {
            'ID': pk,
            'NAME': data.get('first_name'),
            'LAST_NAME': data.get('last_name'),
            'EMAIL': data.get('work_email') or data.get('email'),
            'PERSONAL_MOBILE': data.get('phone'),
            'WORK_POSITION': data.get('designation'),
            'PERSONAL_BIRTHDAY': data.get('dob'),
            'PERSONAL_CITY': data.get('city') or data.get('address_line1'),
            'PERSONAL_STATE': data.get('state'),
            'PERSONAL_ZIP': data.get('pin_code'),
            'PERSONAL_GENDER': gender_code,
            'UF_PERSONAL_EMAIL': data.get('personal_email'),
            'PERSONAL_MAILBOX': data.get('personal_email')
        }
        
        try:
            import requests
            res = requests.post(f"{webhook}/user.update.json", json=payload, timeout=10)
            
            # If the token lacks scope for user.update or fails, fallback to CRM contact update
            if not res.ok:
                update_url_crm = f"{webhook}/crm.contact.update"
                emails_crm = []
                email_val = data.get('work_email') or data.get('email')
                if email_val:
                    emails_crm.append({'VALUE': email_val, 'VALUE_TYPE': 'WORK'})
                if data.get('personal_email'):
                    emails_crm.append({'VALUE': data.get('personal_email'), 'VALUE_TYPE': 'HOME'})
                    
                payload_crm = {
                    'id': pk,
                    'fields': {
                        'NAME': data.get('first_name'),
                        'LAST_NAME': data.get('last_name'),
                        'EMAIL': emails_crm,
                        'PHONE': [{'VALUE': data.get('phone'), 'VALUE_TYPE': 'WORK'}],
                        'POST': data.get('designation'),
                        'UF_PERSONAL_EMAIL': data.get('personal_email'),
                        'PERSONAL_MAILBOX': data.get('personal_email')
                    }
                }
                res = requests.post(update_url_crm, json=payload_crm, timeout=10)
                
            if res.ok:
                # Update local bank details if provided
                bank_account = data.get('bank_account')
                bank_name = data.get('bank_name')
                if bank_account is not None or bank_name is not None:
                    from salary.models import EmployeeBankDetail
                    detail, _ = EmployeeBankDetail.objects.get_or_create(bitrix_user_id=pk)
                    if bank_account is not None:
                        detail.bank_account_no = bank_account
                    if bank_name is not None:
                        detail.bank_name = bank_name
                    detail.save()

                BitrixClient.get_all_users(force_refresh=True)
                user = BitrixClient.get_user_detail(pk)
                
                # Log success in BitrixSyncLog
                try:
                    from notifications.models import BitrixSyncLog
                    BitrixSyncLog.objects.create(
                        employee_id=pk,
                        employee_name=user.get('name') if user else f"{data.get('first_name')} {data.get('last_name')}".strip(),
                        action_type='Contact Update',
                        status='SUCCESS',
                        retry_count=0
                    )
                except Exception:
                    pass

                # Log action
                from audit_logs.signals import log_action
                if request.user.is_authenticated:
                    log_action(request.user, "UPDATE", None, f"Updated Bitrix24 employee details (ID: {pk}).")
                return Response(user)
            else:
                # Log failure in BitrixSyncLog (Trigger 24)
                emp_name = f"{data.get('first_name')} {data.get('last_name')}".strip()
                try:
                    from notifications.models import BitrixSyncLog, Notification
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    
                    BitrixSyncLog.objects.create(
                        employee_id=pk,
                        employee_name=emp_name,
                        action_type='Contact Update',
                        status='FAILED',
                        retry_count=0,
                        error_message=res.text
                    )
                    
                    # Notify Admin (Trigger 24)
                    admins = User.objects.filter(role__code='ADMIN')
                    notif_msg = f"Bitrix24 sync failed for {emp_name} (Contact Update). Retry available."
                    for admin in admins:
                        Notification.objects.create(
                            recipient=admin,
                            notif_type='ERROR',
                            message=notif_msg,
                            link="/admin/bitrix/sync-log/"
                        )
                except Exception:
                    pass

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
            from .tasks import attach_document_to_bitrix24_timeline, send_offer_letter_email
            attach_document_to_bitrix24_timeline.delay(doc.id)
            send_offer_letter_email.delay(employee.id, doc.id)
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
        user = request.user
        is_admin = user.is_superuser or (user.role and user.role.code == 'ADMIN')
        if not is_admin:
            raise PermissionDenied("Only Admin can import employee details.")

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import openpyxl
            wb = openpyxl.load_workbook(file_obj, data_only=True)
            ws = wb.active
        except Exception as e:
            return Response({'error': f'Failed to parse Excel file: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        headers = [str(ws.cell(row=1, column=col).value).strip() for col in range(1, ws.max_column + 1)]
        header_map = {}
        for idx, h in enumerate(headers):
            header_map[h.lower()] = idx + 1

        def get_val(row, header_name, default=""):
            idx = header_map.get(header_name.lower())
            if idx is None:
                return default
            val = ws.cell(row=row, column=idx).value
            return val if val is not None else default

        import datetime
        def parse_date(val):
            if not val:
                return None
            if isinstance(val, (datetime.date, datetime.datetime)):
                return val.date() if isinstance(val, datetime.datetime) else val
            try:
                for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y'):
                    try:
                        return datetime.datetime.strptime(str(val).strip(), fmt).date()
                    except ValueError:
                        continue
            except Exception:
                pass
            return None

        from decimal import Decimal
        def parse_decimal(val):
            if val is None or str(val).strip() == "":
                return Decimal("0.00")
            try:
                cleaned = str(val).strip().replace("$", "").replace(",", "")
                return Decimal(cleaned)
            except Exception:
                return Decimal("0.00")

        total_records = 0
        success_count = 0
        failed_count = 0
        failed_rows_data = []

        from django.db import transaction
        from salary.models import EmployeeBankDetail, SalaryStructure

        # Fetch all active users from Bitrix
        bitrix_users = BitrixClient.get_all_users()

        with transaction.atomic():
            for row_idx in range(2, ws.max_row + 1):
                first_name = str(get_val(row_idx, 'First Name')).strip()
                last_name = str(get_val(row_idx, 'Last Name')).strip()
                if not first_name and not last_name:
                    continue

                total_records += 1
                row_vals = [ws.cell(row=row_idx, column=c).value for c in range(1, ws.max_column + 1)]
                sid = transaction.savepoint()

                try:
                    parsed_emp_id = str(get_val(row_idx, 'Employee ID')).strip()
                    parsed_email = str(get_val(row_idx, 'Email')).strip()
                    parsed_phone = str(get_val(row_idx, 'Phone')).strip()

                    if not parsed_email:
                        raise ValueError("Email is required")

                    # Find matching employee in bitrix_users
                    employee = None
                    for u in bitrix_users:
                        mock_emp = BitrixEmployeeMock(u)
                        if parsed_emp_id and mock_emp.emp_id.lower() == parsed_emp_id.lower():
                            employee = mock_emp
                            break
                        if parsed_email and mock_emp.email.lower() == parsed_email.lower():
                            employee = mock_emp
                            break
                        if parsed_phone and mock_emp.phone == parsed_phone:
                            employee = mock_emp
                            break
                        if mock_emp.name.lower() == f"{first_name} {last_name}".lower().strip():
                            employee = mock_emp
                            break

                    gender_val = str(get_val(row_idx, 'Gender')).strip().upper()
                    gender_code = 'M'
                    if gender_val in ('FEMALE', 'F'):
                        gender_code = 'F'
                    elif gender_val in ('OTHER', 'O'):
                        gender_code = 'O'

                    dept_val = get_val(row_idx, 'Department')
                    dept_list = [1]
                    if dept_val:
                        try:
                            dept_list = [int(float(str(dept_val)))]
                        except ValueError:
                            dept_obj = Department.objects.filter(name__iexact=str(dept_val).strip()).first()
                            if dept_obj:
                                dept_list = [dept_obj.id]

                    webhook = BitrixClient.get_webhook_url()
                    contact_id = None

                    if employee:
                        contact_id = employee.bitrix_id
                        # Update employee details in Bitrix24
                        payload = {
                            'ID': contact_id,
                            'NAME': first_name,
                            'LAST_NAME': last_name,
                            'EMAIL': parsed_email,
                            'PERSONAL_MOBILE': parsed_phone,
                            'WORK_POSITION': str(get_val(row_idx, 'Designation')).strip(),
                            'PERSONAL_BIRTHDAY': str(get_val(row_idx, 'DOB')).strip(),
                            'PERSONAL_CITY': str(get_val(row_idx, 'Address Line 1')).strip(),
                            'PERSONAL_STATE': str(get_val(row_idx, 'State')).strip(),
                            'PERSONAL_ZIP': str(get_val(row_idx, 'PIN Code')).strip(),
                            'PERSONAL_GENDER': gender_code,
                        }
                        
                        import requests
                        res = requests.post(f"{webhook}/user.update.json", json=payload, timeout=10)
                        if not res.ok:
                            payload_crm = {
                                'id': contact_id,
                                'fields': {
                                    'NAME': first_name,
                                    'LAST_NAME': last_name,
                                    'EMAIL': [{'VALUE': parsed_email, 'VALUE_TYPE': 'WORK'}],
                                    'PHONE': [{'VALUE': parsed_phone, 'VALUE_TYPE': 'WORK'}],
                                    'POST': str(get_val(row_idx, 'Designation')).strip(),
                                }
                            }
                            requests.post(f"{webhook}/crm.contact.update", json=payload_crm, timeout=10)
                    else:
                        # Create new contact in Bitrix24
                        user_payload = {
                            'EMAIL': parsed_email,
                            'NAME': first_name,
                            'LAST_NAME': last_name,
                            'PERSONAL_MOBILE': parsed_phone,
                            'WORK_POSITION': str(get_val(row_idx, 'Designation')).strip(),
                            'UF_DEPARTMENT': dept_list,
                            'PERSONAL_BIRTHDAY': str(get_val(row_idx, 'DOB')).strip(),
                            'PERSONAL_GENDER': gender_code,
                        }
                        
                        import requests
                        res = requests.post(f"{webhook}/user.add.json", json=user_payload, timeout=10)
                        if res.ok:
                            contact_id = str(res.json().get('result'))
                        else:
                            crm_payload = {
                                'fields': {
                                    'NAME': first_name,
                                    'LAST_NAME': last_name,
                                    'EMAIL': [{'VALUE': parsed_email, 'VALUE_TYPE': 'WORK'}],
                                    'PHONE': [{'VALUE': parsed_phone, 'VALUE_TYPE': 'WORK'}],
                                    'POST': str(get_val(row_idx, 'Designation')).strip(),
                                    'UF_ONBOARDING_STATUS': 'Pending',
                                    'UF_CRM_ONBOARDING_STATUS': 'Pending',
                                }
                            }
                            res_crm = requests.post(f"{webhook}/crm.contact.add", json=crm_payload, timeout=10)
                            if res_crm.ok:
                                contact_id = str(res_crm.json().get('result'))

                        if not contact_id:
                            # Fallback mock ID
                            import uuid
                            contact_id = f"MOCK-{uuid.uuid4().hex[:8]}"

                    # Save or update Bank details
                    bank_acc = str(get_val(row_idx, 'Bank Account Number')).strip()
                    bank_name = str(get_val(row_idx, 'Bank Name')).strip()
                    if bank_acc or bank_name:
                        EmployeeBankDetail.objects.update_or_create(
                            bitrix_user_id=contact_id,
                            defaults={
                                'bank_account_no': bank_acc,
                                'bank_name': bank_name
                            }
                        )

                    # Save or update Salary Structure
                    gross_salary = parse_decimal(get_val(row_idx, 'Gross Salary'))
                    pf_contribution = parse_decimal(get_val(row_idx, 'PF Contribution'))
                    esi = parse_decimal(get_val(row_idx, 'ESI'))
                    labour_welfare_fund = parse_decimal(get_val(row_idx, 'Labour Welfare Fund'))
                    professional_tax = parse_decimal(get_val(row_idx, 'Professional Tax'))
                    other_deductions = parse_decimal(get_val(row_idx, 'Other Deductions'))
                    
                    salary_eff_from = parse_date(get_val(row_idx, 'Salary Effective From'))
                    joining_date = parse_date(get_val(row_idx, 'Joining Date'))
                    
                    effective_from = salary_eff_from or joining_date or datetime.date.today()

                    SalaryStructure.objects.update_or_create(
                        bitrix_user_id=contact_id,
                        effective_from=effective_from,
                        defaults={
                            'gross_salary': gross_salary,
                            'pf_contribution': pf_contribution,
                            'esi': esi,
                            'labour_welfare_fund': labour_welfare_fund,
                            'professional_tax': professional_tax,
                            'other_deductions': other_deductions
                        }
                    )

                    transaction.savepoint_commit(sid)
                    success_count += 1
                except Exception as e:
                    transaction.savepoint_rollback(sid)
                    failed_count += 1
                    failed_rows_data.append((row_vals, str(e)))

        if failed_count > 0:
            import openpyxl
            from openpyxl import Workbook
            from django.http import HttpResponse
            
            error_wb = Workbook()
            error_ws = error_wb.active
            error_ws.title = "Import Errors"
            error_ws.append(headers + ["Errors"])
            
            for row_vals, err_msg in failed_rows_data:
                padded_vals = list(row_vals) + [""] * (len(headers) - len(row_vals))
                error_ws.append(padded_vals + [err_msg])
                
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="employee_import_errors.xlsx"'
            error_wb.save(response)
            return response

        # Force refresh Bitrix users cache
        BitrixClient.get_all_users(force_refresh=True)

        return Response({
            'message': f'Successfully imported {success_count} employee records.'
        }, status=status.HTTP_201_CREATED)

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
            'Emergency Name', 'Emergency Relationship', 'Emergency Phone', 'Status', 'Onboarding Status',
            'Bank Account Number', 'Bank Name', 'Gross Salary', 'PF Contribution', 'ESI',
            'Labour Welfare Fund', 'Professional Tax', 'Other Deductions', 'Salary Effective From'
        ]
        ws.append(headers)

        from salary.models import EmployeeBankDetail, SalaryStructure

        for emp in queryset:
            detail = EmployeeBankDetail.objects.filter(bitrix_user_id=emp.bitrix_id).first()
            bank_acc = detail.bank_account_no if detail else ""
            bank_nm = detail.bank_name if detail else ""
            
            struct = SalaryStructure.objects.filter(bitrix_user_id=emp.bitrix_id).order_by('-effective_from').first()
            gross_val = float(struct.gross_salary) if struct else 0.0
            pf_val = float(struct.pf_contribution) if struct else 0.0
            esi_val = float(struct.esi) if struct else 0.0
            lwf_val = float(struct.labour_welfare_fund) if struct else 0.0
            pt_val = float(struct.professional_tax) if struct else 0.0
            other_val = float(struct.other_deductions) if struct else 0.0
            eff_val = struct.effective_from.strftime('%Y-%m-%d') if (struct and struct.effective_from) else ""

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
                'Completed' if emp.onboarding_complete else 'Under Onboarding',
                bank_acc,
                bank_nm,
                gross_val,
                pf_val,
                esi_val,
                lwf_val,
                pt_val,
                other_val,
                eff_val
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
        employee_id = self.request.query_params.get('employee_id') or self.request.query_params.get('bitrix_user_id')
        if employee_id:
            queryset = queryset.filter(bitrix_user_id=employee_id)
        return queryset

    def perform_create(self, serializer):
        doc = serializer.save()
        # Log upload in audit logs
        from audit_logs.signals import log_action
        log_action(self.request.user, "UPLOAD", doc, f"Uploaded document '{doc.get_doc_type_display()}' ({doc.original_filename}) for employee {doc.bitrix_user_id}.")
        # Sync to Bitrix24 timeline
        from .tasks import attach_document_to_bitrix24_timeline
        attach_document_to_bitrix24_timeline.delay(doc.id)


from .services import DEFAULT_TEMPLATES


class LetterTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = LetterTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Automatically seed templates if they do not exist
        if LetterTemplate.objects.count() == 0:
            for t in DEFAULT_TEMPLATES:
                LetterTemplate.objects.create(**t)
        else:
            # Overwrite default BOND_LETTER, APPOINTMENT_LETTER, and OFFER_LETTER to align layout instantly
            for t in DEFAULT_TEMPLATES:
                obj = LetterTemplate.objects.filter(name=t['name']).first()
                if obj and t['name'] in ['BOND_LETTER', 'APPOINTMENT_LETTER', 'OFFER_LETTER']:
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


