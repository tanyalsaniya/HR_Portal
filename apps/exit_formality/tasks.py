import os
import logging
import datetime
import requests
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from .models import ExitRequest, ExitFormResponse
from .services import (
    generate_relieving_letter,
    generate_experience_letter,
    generate_notice_letter,
    generate_noc_letter,
    generate_ff_settlement_letter,
    generate_ff_salary_slip
)

logger = logging.getLogger(__name__)

@shared_task
def check_expiring_exit_links():
    from django.utils import timezone
    from .models import ExitSecureLink
    now_dt = timezone.now()
    tomorrow = now_dt + datetime.timedelta(days=1)
    
    # Links that are not used, not expired yet, but expire in less than 24 hours
    links = ExitSecureLink.objects.filter(
        used=False,
        expires_at__gt=now_dt,
        expires_at__lte=tomorrow
    )
    
    for link in links:
        exit_req = link.exit_request
        hr_email = exit_req.initiated_by.email if exit_req.initiated_by else settings.DEFAULT_FROM_EMAIL
        send_mail(
            subject=f"Warning: Exit Link Expiring for {exit_req.employee.first_name} {exit_req.employee.last_name}",
            message=f"The secure exit questionnaire link for {exit_req.employee.first_name} {exit_req.employee.last_name} is expiring within 24 hours (on {link.expires_at}).\n\nPlease resend the link if required.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[hr_email],
            fail_silently=True
        )
    return f"Checked. Sent reminders for {links.count()} links."

@shared_task
def send_exit_documents_after_fully_exited(exit_request_id):
    try:
        exit_req = ExitRequest.objects.get(id=exit_request_id)
        employee = exit_req.employee
    except ExitRequest.DoesNotExist:
        return f"ExitRequest {exit_request_id} not found."

    # Fallback email strategy
    recipient_email = None
    try:
        if hasattr(exit_req, 'form_response') and exit_req.form_response:
            recipient_email = exit_req.form_response.personal_email
    except ExitFormResponse.DoesNotExist:
        pass

    if not recipient_email:
        recipient_email = employee.email  # fallback to work email

    # Generate/Regenerate the selected documents
    selected_doc_types = exit_req.email_documents
    if not isinstance(selected_doc_types, list) or len(selected_doc_types) == 0:
        # Fallback to the default 4 if none specified
        selected_doc_types = ['RELIEVING_LETTER', 'EXPERIENCE_LETTER', 'FF_SETTLEMENT_LETTER', 'FF_SALARY_SLIP']

    docs = []
    if 'RELIEVING_LETTER' in selected_doc_types:
        try:
            docs.append(generate_relieving_letter(exit_req))
        except Exception as e:
            logger.error(f"Error generating RELIEVING_LETTER: {e}")
            
    if 'EXPERIENCE_LETTER' in selected_doc_types:
        try:
            docs.append(generate_experience_letter(exit_req))
        except Exception as e:
            logger.error(f"Error generating EXPERIENCE_LETTER: {e}")
            
    if 'NOTICE_LETTER' in selected_doc_types:
        try:
            docs.append(generate_notice_letter(exit_req))
        except Exception as e:
            logger.error(f"Error generating NOTICE_LETTER: {e}")
            
    if 'NOC_LETTER' in selected_doc_types:
        try:
            docs.append(generate_noc_letter(exit_req))
        except Exception as e:
            logger.error(f"Error generating NOC_LETTER: {e}")
            
    if 'FF_SETTLEMENT_LETTER' in selected_doc_types:
        try:
            docs.append(generate_ff_settlement_letter(exit_req))
        except Exception as e:
            logger.error(f"Error generating FF_SETTLEMENT_LETTER: {e}")
            
    if 'FF_SALARY_SLIP' in selected_doc_types:
        try:
            docs.append(generate_ff_salary_slip(exit_req))
        except Exception as e:
            logger.error(f"Error generating FF_SALARY_SLIP: {e}")


    # Send Email
    subject = f"Your Offboarding Documents - {employee.first_name} {employee.last_name}"
    body = f"Dear {employee.first_name},\n\nPlease find attached your relieving letter, experience certificate, Full & Final settlement statement, and pro-rated salary slip.\n\nSincerely,\nHR Department"
    
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email]
    )
    
    for doc in docs:
        if doc and doc.file:
            try:
                email.attach(doc.original_filename or f"{doc.doc_type}.pdf", doc.file.read(), 'application/pdf')
            except Exception as e:
                logger.error(f"Attachment failed for {doc}: {e}")
                pass
                
    try:
        email.send()
    except Exception as e:
        return f"Email sending failed: {e}"
        
    return f"Documents sent successfully to {recipient_email}."

@shared_task(bind=True, max_retries=3)
def update_bitrix24_on_exit(self, exit_request_id):
    try:
        exit_req = ExitRequest.objects.get(id=exit_request_id)
        employee = exit_req.employee
    except ExitRequest.DoesNotExist:
        return "ExitRequest not found."

    from employee_onboarding.tasks import get_bitrix_webhook
    webhook = get_bitrix_webhook()
    if not webhook or not employee.bitrix_contact_id:
        return "Sync skipped: Webhook or contact ID missing."

    # Update contact status
    payload = {
        'id': employee.bitrix_contact_id,
        'fields': {
            'UF_ONBOARDING_STATUS': 'Exited',
            'UF_CRM_ONBOARDING_STATUS': 'Exited'
        }
    }
    
    try:
        update_url = f"{webhook.rstrip('/')}/crm.contact.update"
        requests.post(update_url, json=payload, timeout=10)
        
        # Timeline note
        activity_url = f"{webhook.rstrip('/')}/crm.activity.add"
        timeline_payload = {
            'fields': {
                'OWNER_TYPE_ID': 3,
                'OWNER_ID': employee.bitrix_contact_id,
                'TYPE_ID': 6,
                'SUBJECT': "Exit Process Completed",
                'COMPLETED': 'Y',
                'DESCRIPTION': f"Employee exited on {exit_req.last_working_day.strftime('%Y-%m-%d')} — F&F processed."
            }
        }
        requests.post(activity_url, json=timeline_payload, timeout=10)
        
        # Timeline PDF attachment
        import base64
        for doc in employee.documents.filter(doc_type__in=['RELIEVING_LETTER', 'EXPERIENCE_LETTER', 'FF_SETTLEMENT_LETTER']):
            try:
                with open(doc.file.path, 'rb') as f:
                    file_content = f.read()
                file_b64 = base64.b64encode(file_content).decode('utf-8')
                
                doc_payload = {
                    'fields': {
                        'OWNER_TYPE_ID': 3,
                        'OWNER_ID': employee.bitrix_contact_id,
                        'TYPE_ID': 6,
                        'SUBJECT': f"Exit Document: {doc.get_doc_type_display()}",
                        'COMPLETED': 'Y',
                        'DESCRIPTION': f"Exit document {doc.get_doc_type_display()} attached.",
                        'WEBDAV_ELEMENTS': [
                            {
                                'fileContent': file_b64,
                                'fileName': doc.original_filename or f"{doc.doc_type}.pdf"
                            }
                        ]
                    }
                }
                requests.post(activity_url, json=doc_payload, timeout=15)
            except Exception:
                pass
                
        return "Bitrix24 contact status and timeline updated."
    except Exception as exc:
        try:
            self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            pass
        return f"Bitrix24 update failed: {exc}"
