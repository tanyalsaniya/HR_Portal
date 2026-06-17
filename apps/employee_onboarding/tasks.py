import os
import requests
import logging
import datetime
from celery import shared_task
from django.conf import settings
from .models import EmployeeDocument

logger = logging.getLogger(__name__)

def get_bitrix_webhook():
    return os.getenv('BITRIX24_WEBHOOK_URL')

@shared_task(bind=True, max_retries=3)
def sync_employee_to_bitrix24(self, employee_id):
    logger.info(f"sync_employee_to_bitrix24 called for {employee_id} (No-op in pure API mode)")
    return "Sync success (no-op in pure API mode)."

@shared_task
def update_bitrix24_onboarding_status(employee_id):
    logger.info(f"update_bitrix24_onboarding_status called for {employee_id} (No-op in pure API mode)")
    return "Status update success (no-op in pure API mode)."

@shared_task
def attach_document_to_bitrix24_timeline(document_id):
    try:
        doc = EmployeeDocument.objects.get(id=document_id)
        bitrix_user_id = doc.bitrix_user_id
    except EmployeeDocument.DoesNotExist:
        return "Document not found."

    webhook = get_bitrix_webhook()
    if not webhook or not bitrix_user_id:
        return "Sync skipped: Webhook or contact ID missing."

    import base64
    try:
        # Read the generated PDF file content
        with open(doc.file.path, 'rb') as f:
            file_content = f.read()
        file_b64 = base64.b64encode(file_content).decode('utf-8')
        
        activity_url = f"{webhook.rstrip('/')}/crm.activity.add"
        payload = {
            'fields': {
                'OWNER_TYPE_ID': 3,  # Contact
                'OWNER_ID': bitrix_user_id,
                'TYPE_ID': 6,  # Document activity
                'SUBJECT': f"Generated {doc.get_doc_type_display()}",
                'COMPLETED': 'Y',
                'DESCRIPTION': f"Letter {doc.get_doc_type_display()} has been generated and saved by HR Portal on {doc.upload_date.strftime('%Y-%m-%d %H:%M')}.",
                'WEBDAV_ELEMENTS': [
                    {
                        'fileContent': file_b64,
                        'fileName': doc.original_filename or f"{doc.doc_type}.pdf"
                    }
                ]
            }
        }
        res = requests.post(activity_url, json=payload, timeout=15)
        if res.ok:
            return "Document attached successfully to Bitrix24 CRM timeline."
        else:
            raise Exception(f"Failed to attach document: {res.text}")
    except Exception as e:
        logger.error(f"Error attaching document to Bitrix24: {e}")
        return f"Attachment failed: {e}"


@shared_task
def send_onboarding_welcome_email(employee_data):
    """
    Sends a welcome and confirmation email to the newly created employee contact,
    with an inline welcome image banner, onboarding date, and checklist of required documents.
    """
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    from email.mime.image import MIMEImage
    
    first_name = employee_data.get('first_name') or ''
    last_name = employee_data.get('last_name') or ''
    full_name = f"{first_name} {last_name}".strip() or "Employee"
    
    emp_id = employee_data.get('emp_id') or employee_data.get('bitrix_contact_id') or 'N/A'
    dept_name = employee_data.get('department_name') or 'N/A'
    manager_name = employee_data.get('manager_name') or 'Prince Parbhakar'
    joining_date = employee_data.get('joining_date') or 'N/A'
    reporting_time = employee_data.get('reporting_time') or '10:00 AM'
    location = employee_data.get('location') or 'Mohali Office'
    
    recipient_email = employee_data.get('personal_email') or employee_data.get('work_email') or employee_data.get('email')
    if not recipient_email:
        logger.warning(f"No recipient email found for onboarding welcome email to {full_name}.")
        return "Failed: No recipient email."
        
    company_name = getattr(settings, 'COMPANY_NAME', 'MTLV Solutions Private Limited')
    
    subject = f"Welcome to {company_name}! - Onboarding Initiated Successfully"
    
    # HTML Email body
    html_content = f"""
    <html>
      <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333333; margin: 0; padding: 0;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; background-color: #ffffff;">
          <div style="text-align: center; background-color: #f8fafc; padding: 10px 0;">
            <img src="cid:welcome_banner" alt="Welcome to the Team" style="max-width: 100%; height: auto; display: block;" />
          </div>
          <div style="padding: 30px;">
            <p style="font-size: 16px; margin-top: 0;">Dear {full_name},</p>
            <p style="font-size: 14px;">Welcome to {company_name}!</p>
            <p style="font-size: 14px;">We are pleased to inform you that your onboarding process has been initiated successfully by the HR team. We are excited to have you join us.</p>
            
            <p style="font-size: 14px; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; color: #1e293b;">Please find your joining details below:</p>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px; margin-bottom: 25px;">
              <tr>
                <td style="padding: 6px 0; font-weight: 600; color: #475569; width: 180px;">Employee ID:</td>
                <td style="padding: 6px 0; color: #0f172a;">{emp_id}</td>
              </tr>
              <tr>
                <td style="padding: 6px 0; font-weight: 600; color: #475569;">Department:</td>
                <td style="padding: 6px 0; color: #0f172a;">{dept_name}</td>
              </tr>
              <tr>
                <td style="padding: 6px 0; font-weight: 600; color: #475569;">Reporting Manager:</td>
                <td style="padding: 6px 0; color: #0f172a;">{manager_name}</td>
              </tr>
              <tr>
                <td style="padding: 6px 0; font-weight: 600; color: #475569;">Joining Date:</td>
                <td style="padding: 6px 0; color: #0f172a;">{joining_date}</td>
              </tr>
              <tr>
                <td style="padding: 6px 0; font-weight: 600; color: #475569;">Reporting Time:</td>
                <td style="padding: 6px 0; color: #0f172a;">{reporting_time}</td>
              </tr>
              <tr>
                <td style="padding: 6px 0; font-weight: 600; color: #475569;">Work Location:</td>
                <td style="padding: 6px 0; color: #0f172a;">{location}</td>
              </tr>
            </table>

            <p style="font-size: 14px; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; color: #1e293b;">Please carry/submit the following documents on your joining date:</p>
            <ul style="font-size: 14px; padding-left: 20px; color: #334155; margin-bottom: 25px;">
              <li style="margin-bottom: 6px;">Government ID Proof (Aadhaar / Passport / Driving License)</li>
              <li style="margin-bottom: 6px;">PAN Card</li>
              <li style="margin-bottom: 6px;">Passport-size Photographs</li>
              <li style="margin-bottom: 6px;">Educational Certificates</li>
              <li style="margin-bottom: 6px;">Previous Employment Documents (if applicable)</li>
              <li style="margin-bottom: 6px;">Address Proof</li>
              <li style="margin-bottom: 6px;">Bank Account Details</li>
              <li style="margin-bottom: 6px;">Signed Offer Letter (if required)</li>
            </ul>

            <p style="font-size: 14px; color: #dc2626; font-weight: 500;">Kindly ensure all documents are available to avoid delays in completing onboarding formalities.</p>
            <p style="font-size: 14px;">If you have any questions, please contact the HR team.</p>
            <p style="font-size: 14px;">We look forward to welcoming you and wish you success in your new role.</p>
            
            <p style="font-size: 14px; margin-top: 30px; margin-bottom: 0;">Best Regards,<br/><strong>HR Team</strong><br/>{company_name}</p>
          </div>
        </div>
      </body>
    </html>
    """
    
    # Text fallback
    text_content = f"""
Dear {full_name},

Welcome to {company_name}!

We are pleased to inform you that your onboarding process has been initiated successfully by the HR team. We are excited to have you join us.

Please find your joining details below:

* Employee ID: {emp_id}
* Department: {dept_name}
* Reporting Manager: {manager_name}
* Joining Date: {joining_date}
* Reporting Time: {reporting_time}
* Work Location: {location}

Please carry/submit the following documents on your joining date:

* Government ID Proof (Aadhaar / Passport / Driving License)
* PAN Card
* Passport-size Photographs
* Educational Certificates
* Previous Employment Documents (if applicable)
* Address Proof
* Bank Account Details
* Signed Offer Letter (if required)

Kindly ensure all documents are available to avoid delays in completing onboarding formalities.

If you have any questions, please contact the HR team.

We look forward to welcoming you and wish you success in your new role.

Best Regards,
HR Team
{company_name}
    """.strip()
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL or 'hr@mtlv.com',
            to=[recipient_email]
        )
        msg.attach_alternative(html_content, "text/html")
        
        # Attach the welcome banner image as inline
        banner_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'welcome_onboarding.png')
        if os.path.exists(banner_path):
            with open(banner_path, 'rb') as f:
                img_data = f.read()
            mime_img = MIMEImage(img_data)
            mime_img.add_header('Content-ID', '<welcome_banner>')
            mime_img.add_header('Content-Disposition', 'inline', filename='welcome_onboarding.png')
            msg.attach(mime_img)
        else:
            logger.warning(f"Welcome banner image not found at {banner_path}, sending without image.")
            
        msg.send(fail_silently=False)
        return f"Welcome email sent successfully to {recipient_email}."
    except Exception as e:
        logger.error(f"Error sending onboarding welcome email to {recipient_email}: {e}")
        return f"Failed to send email: {e}"
