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


@shared_task
def send_exit_initiation_email(exit_request_id):
    """
    Trigger 11: Sends exit initiation email to employee with secure link
    """
    try:
        exit_req = ExitRequest.objects.get(id=exit_request_id)
        emp = exit_req.employee
        link = exit_req.secure_link
    except ExitRequest.DoesNotExist:
        return "Exit request not found."
    except Exception as e:
        return f"Error: {e}"

    recipient_email = emp.personal_email or emp.work_email or emp.email
    if not recipient_email:
        return "No email for employee."

    url = link.get_link()
    subject = "Your Exit Process has been Initiated – MTLV"
    
    # Render or build HTML message
    from django.template.loader import render_to_string
    html_message = None
    try:
        html_message = render_to_string('exit/email_secure_link.html', {
            'employee': emp,
            'exit_request': exit_req,
            'url': url,
            'expiry_days': 7
        })
    except Exception:
        pass

    body = f"""Dear {emp.first_name},

Your offboarding and exit clearance process has been initiated successfully in the MTLV HR Portal.

Your resignation has been acknowledged, and your last working day is confirmed as {exit_req.last_working_day.strftime('%d %b %Y')}.

Please complete your secure exit clearance questionnaire form within 7 days by clicking the link below:
{url}

What happens next:
1. Clearances from IT, Finance, Admin, and Library will be processed.
2. Your Full & Final settlement will be calculated.

Sincerely,
HR Department
MTLV
"""
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False
        )
        return "Exit initiation email sent successfully."
    except Exception as e:
        logger.error(f"Failed to send exit initiation email: {e}")
        return f"Failed: {e}"


@shared_task
def send_exit_form_submission_notification(response_id):
    """
    Trigger 15: Notify HR & Admin and email employee on exit form submission
    """
    from .models import ExitFormResponse
    from notifications.models import Notification
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    try:
        resp = ExitFormResponse.objects.get(id=response_id)
        exit_req = resp.exit_request
        emp = exit_req.employee
    except ExitFormResponse.DoesNotExist:
        return "Form response not found."

    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8000')

    # 1. Notify HR and Admin
    admins = User.objects.filter(role__code='ADMIN')
    hrs = User.objects.filter(role__code='HR')
    
    assets_status = "Returned" if resp.assets_confirmation else "Pending"
    msg = f"{emp.name} has submitted the exit form. Assets: {assets_status} KT Status: {resp.get_kt_status_display()} Reason: {resp.reason_dropdown}"
    
    # In-app + Email for HR
    for hr in hrs:
        Notification.objects.create(
            recipient=hr,
            notif_type='SUCCESS',
            message=msg,
            link=f"/exit/{emp.id}/"
        )
        if hr.email:
            send_mail(
                subject=f"Exit Form Submitted – {emp.name}",
                message=f"{msg}\n\nView details at {frontend_url}/exit/{emp.id}/.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[hr.email],
                fail_silently=True
            )

    # In-app + Email for Admin
    for admin in admins:
        Notification.objects.create(
            recipient=admin,
            notif_type='SUCCESS',
            message=msg,
            link=f"/exit/{emp.id}/"
        )
        if admin.email:
            send_mail(
                subject=f"Exit Form Submitted – {emp.name}",
                message=f"{msg}\n\nView details at {frontend_url}/exit/{emp.id}/.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
                fail_silently=True
            )

    # 2. Email employee confirmation
    recipient_email = resp.personal_email or emp.personal_email or emp.work_email or emp.email
    if recipient_email:
        subject = "Exit Form Received – MTLV"
        body = f"""Dear {emp.first_name},

Thank you for submitting your exit clearance questionnaire form.

Summary of what you submitted:
- Laptop/Assets: {assets_status}
- KT Handover Status: {resp.get_kt_status_display()}
- Handover Recipient: {resp.kt_handover_to or 'N/A'}
- Primary Reason: {resp.reason_dropdown}

Next steps:
- The HR and Admin teams will verify your submissions and asset returns.
- Your clearances will be updated, and Full & Final (F&F) settlement calculations will proceed.

Best Regards,
HR Team
MTLV
"""
        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False
            )
        except Exception as e:
            logger.error(f"Failed to send exit form submission email: {e}")

    return "Exit form submission notifications sent."
