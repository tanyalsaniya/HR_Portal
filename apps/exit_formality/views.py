import datetime
from django.shortcuts import get_object_or_404, render
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal
from rest_framework import viewsets, status, serializers
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied

from roles.permissions import HasModelPermission
from employee_onboarding.models import Department
from common.bitrix_client import BitrixClient, BitrixEmployeeMock
from employee_onboarding.serializers import EmployeeSerializer, EmployeeDocumentSerializer
from .models import ExitRequest, ExitSecureLink, ExitFormResponse, ExitFFSettlement
from .serializers import ExitRequestSerializer, ExitFormResponseSerializer, ExitFFSettlementSerializer
from .services import (
    generate_relieving_letter, generate_experience_letter, generate_notice_letter,
    generate_noc_letter, generate_ff_settlement_letter, generate_ff_salary_slip,
    render_exit_letter_to_html
)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class ExitRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ExitRequestSerializer
    permission_classes = [HasModelPermission]

    def get_queryset(self):
        return ExitRequest.objects.all().order_by('-initiated_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        no_pagination = request.query_params.get('no_pagination') == 'true'
        if not no_pagination:
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        bitrix_user_id = serializer.validated_data.get('bitrix_user_id')
        if not bitrix_user_id:
            raise ValidationError("bitrix_user_id is required.")
        user_data = BitrixClient.get_user_detail(bitrix_user_id)
        if not user_data:
            raise ValidationError("Employee not found in Bitrix24.")
        employee = BitrixEmployeeMock(user_data)
        
        # Check if employee is already exited
        if employee.status == 'Exited':
            raise ValidationError("This employee has already exited the company.")
            
        resignation_date = serializer.validated_data['resignation_date']
        notice_period_waiver = serializer.validated_data.get('notice_period_waiver', False)
        
        # Calculate last working day
        if notice_period_waiver:
            last_working_day = serializer.validated_data.get('last_working_day', resignation_date)
        else:
            last_working_day = resignation_date + datetime.timedelta(days=employee.notice_period_days)
            
        exit_req = serializer.save(
            last_working_day=last_working_day,
            status='PENDING'
        )
        
        # Create ExitSecureLink if not absconding
        if exit_req.exit_type != 'ABSCONDING':
            from rules import EXIT_LINK_EXPIRY_DAYS
            expires_at = timezone.now() + datetime.timedelta(days=EXIT_LINK_EXPIRY_DAYS)
            link = ExitSecureLink.objects.create(
                exit_request=exit_req,
                expires_at=expires_at
            )
            
            # Save secure link sent/expiry times
            exit_req.secure_link_sent_at = timezone.now()
            exit_req.secure_link_expires_at = expires_at
            exit_req.save(update_fields=['secure_link_sent_at', 'secure_link_expires_at'])
            
            # Send secure link email
            self._send_email_link(exit_req, link)
        
        # Auto generate Notice Letter if requested
        if exit_req.notice_letter_required:
            generate_notice_letter(exit_req, user=self.request.user)

    def _send_email_link(self, exit_req, link):
        recipient = exit_req.employee.email
        url = link.get_link()
        from django.template.loader import render_to_string
        html_message = render_to_string('exit/email_secure_link.html', {
            'employee': exit_req.employee,
            'exit_request': exit_req,
            'url': url,
            'expiry_days': 7
        })
        send_mail(
            subject="Action Required: Exit Clearance Questionnaire",
            message=f"Dear {exit_req.employee.first_name},\n\nPlease complete your offboarding exit clearance form within 7 days by clicking the following link:\n{url}\n\nSincerely,\nHR Department",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message,
            fail_silently=False
        )

    @action(detail=True, methods=['POST'], url_path='send-link', url_name='send-link')
    def send_link_api(self, request, pk=None):
        exit_req = self.get_object()
        link = getattr(exit_req, 'secure_link', None)
        if not link or not link.is_valid():
            from rules import EXIT_LINK_EXPIRY_DAYS
            expires_at = timezone.now() + datetime.timedelta(days=EXIT_LINK_EXPIRY_DAYS)
            if link:
                import uuid
                link.token = uuid.uuid4()
                link.used = False
                link.used_at = None
                link.expires_at = expires_at
                link.save()
            else:
                link = ExitSecureLink.objects.create(
                    exit_request=exit_req,
                    expires_at=expires_at
                )
            exit_req.secure_link_sent_at = timezone.now()
            exit_req.secure_link_expires_at = expires_at
            exit_req.save(update_fields=['secure_link_sent_at', 'secure_link_expires_at'])
            
        self._send_email_link(exit_req, link)
        return Response({'message': 'Exit link emailed successfully.'})

    @action(detail=True, methods=['POST'], url_path='resend-link', url_name='resend-link')
    def resend_link(self, request, pk=None):
        exit_req = self.get_object()
        link = getattr(exit_req, 'secure_link', None)
        from rules import EXIT_LINK_EXPIRY_DAYS
        expires_at = timezone.now() + datetime.timedelta(days=EXIT_LINK_EXPIRY_DAYS)
        if link:
            import uuid
            link.token = uuid.uuid4()
            link.used = False
            link.used_at = None
            link.expires_at = expires_at
            link.save()
        else:
            link = ExitSecureLink.objects.create(
                exit_request=exit_req,
                expires_at=expires_at
            )
        exit_req.secure_link_sent_at = timezone.now()
        exit_req.secure_link_expires_at = expires_at
        exit_req.save(update_fields=['secure_link_sent_at', 'secure_link_expires_at'])
        
        self._send_email_link(exit_req, link)
        return Response({'message': 'New exit link generated and sent.'})

    @action(detail=True, methods=['PUT'], url_path='cancel', url_name='cancel')
    def cancel(self, request, pk=None):
        exit_req = self.get_object()
        cancelled_reason = request.data.get('cancelled_reason')
        if not cancelled_reason or not cancelled_reason.strip():
            raise ValidationError({'cancelled_reason': 'Cancellation reason is required.'})
            
        exit_req.status = 'CANCELLED'
        exit_req.cancelled_reason = cancelled_reason
        exit_req.save(update_fields=['status', 'cancelled_reason'])
        
        # Reset employee to Active in Bitrix24
        webhook = BitrixClient.get_webhook_url()
        update_url = f"{webhook}/crm.contact.update"
        try:
            import requests
            requests.post(update_url, json={
                'id': exit_req.bitrix_user_id,
                'fields': {
                    'UF_ONBOARDING_STATUS': 'Completed',
                }
            }, timeout=10)
            BitrixClient.get_all_users(force_refresh=True)
        except Exception:
            pass
        
        return Response({'message': 'Exit request cancelled successfully.'})

    @action(detail=True, methods=['PUT'], url_path='override', url_name='override')
    def override(self, request, pk=None):
        exit_req = self.get_object()
        override_reason = request.data.get('override_reason')
        if not override_reason or not override_reason.strip():
            raise ValidationError({'override_reason': 'Override reason is required.'})
            
        exit_req.status = 'OVERRIDDEN'
        exit_req.override_reason = override_reason
        exit_req.overridden_by = request.user
        exit_req.overridden_at = timezone.now()
        exit_req.save(update_fields=['status', 'override_reason', 'overridden_by', 'overridden_at'])
        
        return Response({'message': 'Exit request status overridden successfully.'})

    @action(detail=True, methods=['PUT'], url_path='reopen', url_name='reopen')
    def reopen(self, request, pk=None):
        exit_req = self.get_object()
        exit_req.status = 'REOPENED'
        exit_req.save(update_fields=['status'])
        
        # Reset employee to Active in Bitrix24
        webhook = BitrixClient.get_webhook_url()
        update_url = f"{webhook}/crm.contact.update"
        try:
            import requests
            requests.post(update_url, json={
                'id': exit_req.bitrix_user_id,
                'fields': {
                    'UF_ONBOARDING_STATUS': 'Completed',
                }
            }, timeout=10)
            BitrixClient.get_all_users(force_refresh=True)
        except Exception:
            pass
        
        return Response({'message': 'Exit request reopened successfully.'})

    @action(detail=True, methods=['POST'], url_path='mark-fully-exited')
    def mark_fully_exited(self, request, pk=None):
        exit_req = self.get_object()
        ff = getattr(exit_req, 'ff_settlement', None)
        if not ff or not ff.approved_by:
            raise ValidationError('F&F Settlement must be completed and approved before marking as fully exited.')
            
        send_email = request.data.get('send_email', True)
        if isinstance(send_email, str):
            send_email = send_email.lower() == 'true'
            
        if send_email:
            user = request.user
            is_admin = user.is_superuser or (user.role and user.role.code == 'ADMIN')
            if not is_admin:
                user_perms = list(user.role.permissions.values_list('codename', flat=True)) if user.role else []
                if 'exit.send_email' not in user_perms:
                    raise PermissionDenied("You do not have permission to dispatch exit documents via email.")

        exit_req.send_email_on_exit = send_email
        
        email_docs = request.data.get('email_documents', [])
        if isinstance(email_docs, list):
            exit_req.email_documents = email_docs
            
        exit_req.status = 'FULLY_EXITED'
        exit_req.save(update_fields=['status', 'send_email_on_exit', 'email_documents'])
        return Response({'message': 'Employee marked as Fully Exited. Final documents are being dispatched.'})

    @action(detail=True, methods=['PUT'], url_path='extend-lwd')
    def extend_lwd(self, request, pk=None):
        exit_req = self.get_object()
        lwd_str = request.data.get('last_working_day')
        if not lwd_str:
            raise ValidationError({'last_working_day': 'New last working day date is required.'})
        try:
            new_lwd = datetime.datetime.strptime(lwd_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError({'last_working_day': 'Invalid date format. Use YYYY-MM-DD.'})
            
        exit_req.last_working_day = new_lwd
        exit_req.save(update_fields=['last_working_day'])
        return Response({'message': 'Last working day extended successfully.', 'last_working_day': exit_req.last_working_day})

    @action(detail=True, methods=['PUT'], url_path='update-clearances')
    def update_clearances(self, request, pk=None):
        exit_req = self.get_object()
        updated = False
        for field in ['clearance_it', 'clearance_finance', 'clearance_admin', 'clearance_manager', 'clearance_library']:
            if field in request.data:
                val = request.data[field]
                if val in ['PENDING', 'CLEARED', 'NA']:
                    setattr(exit_req, field, val)
                    updated = True
                    
        if updated:
            clearances = [
                exit_req.clearance_it, exit_req.clearance_finance,
                exit_req.clearance_admin, exit_req.clearance_manager,
                exit_req.clearance_library
            ]
            if all(c in ('CLEARED', 'NA') for c in clearances):
                if exit_req.status in ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'REOPENED'):
                    exit_req.status = 'CLEARANCES_DONE'
            exit_req.save()
            
        return Response({
            'message': 'Clearance checklist updated.',
            'status': exit_req.status,
            'clearances': {
                'clearance_it': exit_req.clearance_it,
                'clearance_finance': exit_req.clearance_finance,
                'clearance_admin': exit_req.clearance_admin,
                'clearance_manager': exit_req.clearance_manager,
                'clearance_library': exit_req.clearance_library
            }
        })

    @action(detail=True, methods=['PUT'], url_path='update-it-checklist')
    def update_it_checklist(self, request, pk=None):
        exit_req = self.get_object()
        updated = False
        for field in [
            'it_email_deactivated', 'it_system_access_revoked', 'it_vpn_removed',
            'it_biometric_deactivated', 'it_data_backup_completed'
        ]:
            if field in request.data:
                setattr(exit_req, field, bool(request.data[field]))
                updated = True
                
        if updated:
            exit_req.save()
            
        return Response({
            'message': 'IT revocation checklist updated.',
            'it_checklist': {
                'it_email_deactivated': exit_req.it_email_deactivated,
                'it_system_access_revoked': exit_req.it_system_access_revoked,
                'it_vpn_removed': exit_req.it_vpn_removed,
                'it_biometric_deactivated': exit_req.it_biometric_deactivated,
                'it_data_backup_completed': exit_req.it_data_backup_completed
            }
        })

    @action(detail=True, methods=['POST'], url_path='process-ff', url_name='process-ff')
    def process_ff(self, request, pk=None):
        exit_req = self.get_object()
        data = request.data.copy()
        
        try:
            salary_proportional = Decimal(str(data.get('salary_proportional', 0)))
            leave_encashment_amount = Decimal(str(data.get('leave_encashment_amount', 0)))
            bonus_arrears = Decimal(str(data.get('bonus_arrears', 0)))
            gratuity_amount = Decimal(str(data.get('gratuity_amount', 0)))
            
            reimbursements_json = data.get('reimbursements_json', [])
            if isinstance(reimbursements_json, str):
                import json
                reimbursements_json = json.loads(reimbursements_json)
            reimb_total = sum(Decimal(str(r.get('amount', 0))) for r in reimbursements_json)
            
            total_earnings = salary_proportional + leave_encashment_amount + bonus_arrears + gratuity_amount + reimb_total
            
            notice_shortfall_amount = Decimal(str(data.get('notice_shortfall_amount', 0)))
            salary_advance_outstanding = Decimal(str(data.get('salary_advance_outstanding', 0)))
            bond_penalty = Decimal(str(data.get('bond_penalty', 0)))
            tds_deduction = Decimal(str(data.get('tds_deduction', 0)))
            
            other_deductions_json = data.get('other_deductions_json', [])
            if isinstance(other_deductions_json, str):
                import json
                other_deductions_json = json.loads(other_deductions_json)
            ded_total = sum(Decimal(str(d.get('amount', 0))) for d in other_deductions_json)
            
            total_deductions = notice_shortfall_amount + salary_advance_outstanding + bond_penalty + tds_deduction + ded_total
            net_payable = total_earnings - total_deductions
            
            data['total_earnings'] = total_earnings
            data['total_deductions'] = total_deductions
            data['net_payable'] = net_payable
        except Exception as e:
            raise ValidationError(f"Error calculating F&F totals: {str(e)}")
            
        try:
            ff_settlement = exit_req.ff_settlement
            serializer = ExitFFSettlementSerializer(ff_settlement, data=data, context={'exit_request': exit_req})
        except ExitFFSettlement.DoesNotExist:
            serializer = ExitFFSettlementSerializer(data=data, context={'exit_request': exit_req})
            
        serializer.is_valid(raise_exception=True)
        ff_settlement = serializer.save(exit_request=exit_req, created_by=request.user)
        
        if exit_req.status == 'CLEARANCES_DONE':
            exit_req.status = 'FF_PROCESSED'
            exit_req.save(update_fields=['status'])
            
        return Response({
            'message': 'F&F calculations saved.',
            'ff_settlement': ExitFFSettlementSerializer(ff_settlement).data
        })

    @action(detail=True, methods=['POST'], url_path='approve-ff', url_name='approve-ff')
    def approve_ff(self, request, pk=None):
        exit_req = self.get_object()
        try:
            ff_settlement = exit_req.ff_settlement
        except ExitFFSettlement.DoesNotExist:
            raise ValidationError("F&F calculations must be processed before approval.")
            
        ff_settlement.approved_by = request.user
        ff_settlement.approved_at = timezone.now()
        ff_settlement.save(update_fields=['approved_by', 'approved_at'])
        
        if exit_req.status in ('CLEARANCES_DONE', 'COMPLETED', 'IN_PROGRESS', 'PENDING'):
            exit_req.status = 'FF_PROCESSED'
            exit_req.save(update_fields=['status'])
            
        return Response({
            'message': 'F&F settlement approved successfully.',
            'ff_settlement': ExitFFSettlementSerializer(ff_settlement).data
        })

    @action(detail=True, methods=['POST'], url_path='preview-letter')
    def preview_letter(self, request, pk=None):
        exit_req = self.get_object()
        doc_type = request.data.get('doc_type')
        type_map = {
            'relieving': 'RELIEVING_LETTER',
            'experience': 'EXPERIENCE_LETTER',
            'notice': 'NOTICE_LETTER',
            'noc': 'NOC_LETTER',
            'ff-letter': 'FF_SETTLEMENT_LETTER',
            'ff-slip': 'FF_SALARY_SLIP',
        }
        mapped_type = type_map.get(doc_type, doc_type)
        if not mapped_type:
            raise ValidationError({'doc_type': 'This field is required.'})
            
        custom_context = request.data.get('custom_context', {})
        try:
            html_content = render_exit_letter_to_html(exit_req, mapped_type, custom_context)
            return Response({'html': html_content})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-relieving')
    def generate_relieving_api(self, request, pk=None):
        exit_req = self.get_object()
        if exit_req.status not in ('COMPLETED', 'CLEARANCES_DONE', 'FF_PROCESSED', 'FULLY_EXITED'):
            return Response({
                'error': 'Relieving letter can only be generated after exit questionnaire is completed.'
            }, status=status.HTTP_400_BAD_REQUEST)
        custom_context = request.data.get('custom_context', None)
        try:
            doc = generate_relieving_letter(exit_req, user=request.user, custom_context=custom_context)
            return Response({
                'message': 'Relieving letter generated.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-experience')
    def generate_experience_api(self, request, pk=None):
        exit_req = self.get_object()
        if exit_req.status not in ('COMPLETED', 'CLEARANCES_DONE', 'FF_PROCESSED', 'FULLY_EXITED'):
            return Response({
                'error': 'Experience letter can only be generated after exit questionnaire is completed.'
            }, status=status.HTTP_400_BAD_REQUEST)
        custom_context = request.data.get('custom_context', None)
        try:
            doc = generate_experience_letter(exit_req, user=request.user, custom_context=custom_context)
            return Response({
                'message': 'Experience letter generated.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-notice')
    def generate_notice_api(self, request, pk=None):
        exit_req = self.get_object()
        custom_context = request.data.get('custom_context', None)
        try:
            doc = generate_notice_letter(exit_req, user=request.user, custom_context=custom_context)
            return Response({
                'message': 'Notice letter generated.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-noc', url_name='generate-noc')
    def generate_noc_api(self, request, pk=None):
        exit_req = self.get_object()
        custom_context = request.data.get('custom_context', None)
        try:
            doc = generate_noc_letter(exit_req, user=request.user, custom_context=custom_context)
            return Response({
                'message': 'NOC generated successfully.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-ff-letter')
    def generate_ff_letter_api(self, request, pk=None):
        exit_req = self.get_object()
        custom_context = request.data.get('custom_context', None)
        try:
            doc = generate_ff_settlement_letter(exit_req, user=request.user, custom_context=custom_context)
            return Response({
                'message': 'F&F Settlement letter generated.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['POST'], url_path='generate-ff-slip')
    def generate_ff_slip_api(self, request, pk=None):
        exit_req = self.get_object()
        custom_context = request.data.get('custom_context', None)
        try:
            doc = generate_ff_salary_slip(exit_req, user=request.user, custom_context=custom_context)
            return Response({
                'message': 'Final month salary slip generated.',
                'document': EmployeeDocumentSerializer(doc).data
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ExitPublicQuestionnaireView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        ip = get_client_ip(request)
        cache_key = f"exit_rate_limit_{ip}"
        requests_count = cache.get(cache_key, 0)
        if requests_count >= 10:
            return Response({'error': 'Rate limit exceeded. Try again in an hour.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        cache.set(cache_key, requests_count + 1, 3600)
        
        token_str = request.query_params.get('token')
        if not token_str:
            return Response({'error': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            link = ExitSecureLink.objects.get(token=token_str)
        except (ExitSecureLink.DoesNotExist, ValidationError):
            return Response({'error': 'Invalid exit link token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not link.is_valid():
            return Response({'error': 'This exit link has expired or has already been used.'}, status=status.HTTP_410_GONE)

        # Log IP on first access
        if not link.ip_address:
            link.ip_address = ip
            link.save(update_fields=['ip_address'])

        exit_request = link.exit_request
        employee = exit_request.employee
        
        if exit_request.status == 'PENDING':
            exit_request.status = 'IN_PROGRESS'
            exit_request.save(update_fields=['status'])
            
        form_data = {}
        try:
            form_response = exit_request.form_response
            form_data = ExitFormResponseSerializer(form_response).data
        except ExitFormResponse.DoesNotExist:
            pass
            
        return Response({
            'exit_request_id': exit_request.id,
            'employee_name': f"{employee.first_name} {employee.last_name}",
            'employee_id': employee.emp_id,
            'last_working_day': exit_request.last_working_day,
            'form_data': form_data
        })

    def post(self, request):
        ip = get_client_ip(request)
        cache_key = f"exit_rate_limit_{ip}"
        requests_count = cache.get(cache_key, 0)
        if requests_count >= 10:
            return Response({'error': 'Rate limit exceeded. Try again in an hour.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        cache.set(cache_key, requests_count + 1, 3600)
        
        token_str = request.data.get('token')
        if not token_str:
            return Response({'error': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            link = ExitSecureLink.objects.get(token=token_str)
        except (ExitSecureLink.DoesNotExist, ValidationError):
            return Response({'error': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not link.is_valid():
            return Response({'error': 'This link is expired or already used.'}, status=status.HTTP_410_GONE)

        exit_req = link.exit_request
        is_draft = request.data.get('is_draft', False)
        
        if not is_draft:
            if not request.data.get('declaration_confirmed', False):
                return Response({'error': 'Declaration must be confirmed for final submission.'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.data.copy()
        
        if is_draft:
            data.setdefault('kt_status', 'IN_PROGRESS')
            data.setdefault('reason_dropdown', 'Other')
            data.setdefault('reason_details', 'Draft save')
            data.setdefault('rating_env', 5)
            data.setdefault('rating_mgmt', 5)
            data.setdefault('recommend', 'Maybe')
            data.setdefault('personal_email', exit_req.employee.email)
            
        try:
            form_response = exit_req.form_response
            serializer = ExitFormResponseSerializer(form_response, data=data, partial=is_draft)
        except ExitFormResponse.DoesNotExist:
            serializer = ExitFormResponseSerializer(data=data)
            
        serializer.is_valid(raise_exception=True)
        form_response = serializer.save(exit_request=exit_req)
        
        if not is_draft:
            link.used = True
            link.used_at = timezone.now()
            link.save(update_fields=['used', 'used_at'])
            
        return Response({
            'message': 'Draft saved successfully.' if is_draft else 'Your exit questionnaire has been submitted successfully.',
            'form_data': ExitFormResponseSerializer(form_response).data
        }, status=status.HTTP_200_OK if is_draft else status.HTTP_201_CREATED)

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
        
        salary_data = request.data.get('salary_structure')
        
        if not all([ex_employee_id, new_joining_date, new_designation, new_department_id, new_employment_type, salary_data]):
            return Response({'error': 'All details and salary structure are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            ex_employee_data = BitrixClient.get_user_detail(ex_employee_id)
            if not ex_employee_data:
                raise Exception()
            ex_employee = BitrixEmployeeMock(ex_employee_data)
        except Exception:
            return Response({'error': 'Ex-employee record not found in Bitrix24.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            dept = Department.objects.get(id=new_department_id)
        except Department.DoesNotExist:
            return Response({'error': 'Department not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Update designation and active status in Bitrix24
        webhook = BitrixClient.get_webhook_url()
        update_url = f"{webhook}/crm.contact.update"
        payload = {
            'id': ex_employee_id,
            'fields': {
                'POST': new_designation,
                'UF_ONBOARDING_STATUS': 'Pending',
                'UF_CRM_ONBOARDING_STATUS': 'Pending'
            }
        }
        try:
            import requests
            requests.post(update_url, json=payload, timeout=10)
        except Exception:
            pass

        # Refresh Bitrix cache
        BitrixClient.get_all_users(force_refresh=True)
        new_emp_data = BitrixClient.get_user_detail(ex_employee_id)
        new_emp = BitrixEmployeeMock(new_emp_data)

        from salary.models import SalaryStructure
        from salary.serializers import SalaryStructureSerializer
        
        salary_structure_data = salary_data.copy()
        salary_structure_data['bitrix_user_id'] = ex_employee_id
        
        salary_serializer = SalaryStructureSerializer(data=salary_structure_data, context={'request': request})
        if not salary_serializer.is_valid():
            return Response(salary_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        salary_serializer.save(created_by=request.user)

        return Response({
            'message': 'Ex-employee rejoined successfully in Bitrix24 and new salary structure applied.',
            'employee': EmployeeSerializer(new_emp._data).data
        }, status=status.HTTP_201_CREATED)

def exit_form_view(request, token):
    return render(request, 'exit/questionnaire.html', {'token': token})
