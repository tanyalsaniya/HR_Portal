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
    designation = employee_data.get('designation') or 'Jr. Python Developer'
    reporting_time = employee_data.get('reporting_time') or '9:30 AM'
    location = employee_data.get('location') or 'Mohali Office'
    
    recipient_email = employee_data.get('personal_email') or employee_data.get('work_email') or employee_data.get('email')
    if not recipient_email:
        logger.warning(f"No recipient email found for onboarding welcome email to {full_name}.")
        return "Failed: No recipient email."
        
    company_name = getattr(settings, 'COMPANY_NAME', 'Devex Hub Pvt Ltd')
    
    subject = f"Congratulations..!! Selection at {company_name}"
    
    # Format joining date to e.g. 22-June-2026 (Monday)
    import datetime
    joining_date_str = joining_date
    try:
        if isinstance(joining_date, (datetime.date, datetime.datetime)):
            dt = joining_date
        else:
            dt = datetime.datetime.strptime(str(joining_date).strip(), '%Y-%m-%d')
        joining_date_formatted = dt.strftime('%d-%B-%Y')
        day_name = dt.strftime('%A')
        joining_date_str = f"{joining_date_formatted} ({day_name})"
    except Exception:
        pass

    # HTML Email body
    html_content = f"""
    <html>
      <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 40px 0;">
        <table align="center" border="0" cellpadding="0" cellspacing="0" width="600" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); overflow: hidden;">
          <tr>
            <td align="center" style="padding: 30px 0 20px 0; background-color: #ffffff; border-bottom: 2px solid #f0f0f0;">
              <img src="cid:company_logo" alt="Devex Hub Logo" style="display: block; max-width: 180px; height: auto;" />
            </td>
          </tr>
          <tr>
            <td style="padding: 40px 40px 20px 40px; color: #333333; font-size: 15px; line-height: 1.6;">
              <p style="margin-top: 0; font-size: 16px;">Dear {first_name},</p>
              
              <p style="color: #2c3e50; font-size: 18px; font-weight: bold; margin: 20px 0;">Congratulations..!!</p>
              
              <p style="margin-bottom: 20px;">We would like to inform you that you have been selected as the best candidate for the position of <strong>{designation}</strong> at Devex Hub Pvt Ltd. Your Joining date will be <strong>{joining_date_str}</strong> and you have to report at <strong>{reporting_time}</strong>. We believe that your knowledge, skills and experience would be an ideal fit for our company. We hope you will enjoy your role and make a significant contribution to the overall success of Devex Hub Pvt Ltd.</p>
              
              <div style="background-color: #f8fbfa; border-left: 4px solid #2980b9; padding: 15px 20px; margin: 25px 0;">
                  <p style="margin-top: 0; font-weight: 600; color: #2c3e50;">Kindly carry original + Photo copies of below mentioned documents that we need at the time of your joining and please share soft copies as well.</p>
                  
                  <ul style="margin: 10px 0 0 0; padding-left: 20px; color: #444444;">
                      <li style="margin-bottom: 5px;">Aadhar Card.</li>
                      <li style="margin-bottom: 5px;">Pan Card.</li>
                      <li style="margin-bottom: 5px;">Two Passport Size Photos.</li>
                      <li style="margin-bottom: 5px;">Higher Qualification Certificate.</li>
                      <li style="margin-bottom: 5px;">Bank Account Details.</li>
                      <li style="margin-bottom: 0;">Previous Experience Letters and salary slips.</li>
                  </ul>
              </div>
              
              <p style="margin-bottom: 20px;">Please accept this letter and send us your acknowledgement.</p>
              
              <p style="margin-bottom: 30px;">If you have any questions and concerns then feel free to contact us back. Looking forward to working with you at Devex Hub Pvt Ltd.</p>
              
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="color: #555555; font-size: 14px; line-height: 1.5;">
                    <p style="margin: 0 0 10px 0;">Regards,</p>
                    <p style="margin: 0; font-weight: bold; color: #333333; font-size: 15px;">NEHA ARYA</p>
                    <p style="margin: 2px 0; color: #777777;">Sr. HR</p>
                    <p style="margin: 2px 0;">Devex Hub Pvt Ltd</p>
                    <p style="margin: 2px 0;">#254, GR Square, Fourth Floor</p>
                    <p style="margin: 2px 0;">Phase 8A, Industrial Area, Mohali</p>
                    <p style="margin: 2px 0;">India, 160055</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td align="center" style="background-color: #2c3e50; padding: 15px; color: #ffffff; font-size: 13px;">
              Website: <a href="http://www.devexhub.com" style="color: #3498db; text-decoration: none; font-weight: bold;">www.devexhub.com</a>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
    
    # Text fallback
    text_content = f"""
Dear {first_name},

Congratulations..!!

We would like to inform you that you have been selected as the best candidate for the position of {designation} at Devex Hub Pvt Ltd. Your Joining date will be {joining_date_str} and you have to report at {reporting_time}. We believe that your knowledge, skills and experience would be an ideal fit for our company. We hope you will enjoy your role and make a significant contribution to the overall success of Devex Hub Pvt Ltd.

Kindly carry original + Photo copies of below mentioned documents that we need at the time of your joining and please share soft copies as well.

• Aadhar Card.
• Pan Card.
• Two Passport Size Photos.
• Higher Qualification Certificate.
• Bank Account Details.
• Previous Experience Letters and salary slips.

Please accept this letter and send us your acknowledgement.

If you have any questions and concerns then feel free to contact us back. Looking forward to working with you at Devex Hub Pvt Ltd.


Regards,

NEHA ARYA
Sr. HR
Devex Hub Pvt Ltd
#254, GR Square, Fourth Floor
Phase 8A, Industrial Area, Mohali
India, 160055

Website: www.devexhub.com
    """.strip()
    try:
        from_name = "Devex Hub HR"
        from_email_addr = settings.DEFAULT_FROM_EMAIL or 'hr@mtlv.com'
        formatted_from = f"{from_name} <{from_email_addr}>"
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=formatted_from,
            to=[recipient_email]
        )
        msg.mixed_subtype = 'related'  # Required for inline CID images to work in Gmail
        msg.attach_alternative(html_content, "text/html")
        
        # Attach the company logo image as inline
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'DevEx Hub logo.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                img_data = f.read()
            mime_img = MIMEImage(img_data)
            mime_img.add_header('Content-ID', '<company_logo>')
            mime_img.add_header('Content-Disposition', 'inline', filename='DevEx Hub logo.png')
            msg.attach(mime_img)
        else:
            logger.warning(f"Company logo image not found at {logo_path}, sending without image.")
            
        msg.send(fail_silently=False)
        return f"Welcome email sent successfully to {recipient_email}."
    except Exception as e:
        logger.error(f"Error sending onboarding welcome email to {recipient_email}: {e}")
        return f"Failed to send email: {e}"


@shared_task
def send_offer_letter_email(employee_id, doc_id):
    """
    Sends the generated Offer Letter PDF via email to the employee.
    """
    from django.core.mail import EmailMessage
    from django.conf import settings
    from .models import EmployeeDocument
    from common.bitrix_client import BitrixClient, BitrixEmployeeMock

    try:
        user_detail = BitrixClient.get_user_detail(employee_id)
        if not user_detail:
            return "Employee not found."
        emp = BitrixEmployeeMock(user_detail)
        doc = EmployeeDocument.objects.get(id=doc_id)
    except Exception as err:
        return f"Error loading data: {err}"

    recipient_email = emp.personal_email or emp.work_email or emp.email
    if not recipient_email:
        return "No email for employee."

    subject = "Your Offer Letter – Devex Hub Pvt Ltd."
    body = f"""Dear {emp.first_name},

Please find attached your official Offer Letter from Devex Hub Pvt Ltd.

If you have any questions or need further details, feel free to contact the HR team.

Best Regards,
HR Team
Devex Hub Pvt Ltd.
"""
    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL or 'hr@mtlv.com',
            to=[recipient_email]
        )
        if doc.file:
            email.attach(doc.original_filename or "Offer_Letter.pdf", doc.file.read(), 'application/pdf')
        email.send(fail_silently=False)
        return "Offer letter sent successfully."
    except Exception as e:
        logger.error(f"Failed to send offer letter email to {recipient_email}: {e}")
        return f"Failed: {e}"


def save_synced_employee_to_db(mock_user):
    if not mock_user or not mock_user.get('id'):
        return
    try:
        from .models import SyncedEmployee
        def parse_date_str(val):
            if not val:
                return None
            if isinstance(val, (datetime.date, datetime.datetime)):
                return val.date() if isinstance(val, datetime.datetime) else val
            try:
                return datetime.datetime.strptime(str(val).strip(), '%Y-%m-%d').date()
            except Exception:
                return None
        
        dob_val = parse_date_str(mock_user.get('dob'))
        joining_date_val = parse_date_str(mock_user.get('joining_date'))
        
        SyncedEmployee.objects.update_or_create(
            bitrix_user_id=str(mock_user.get('id')),
            defaults={
                'first_name': mock_user.get('first_name') or mock_user.get('name') or 'N/A',
                'last_name': mock_user.get('last_name') or '',
                'email': mock_user.get('email') or mock_user.get('work_email') or mock_user.get('personal_email') or '',
                'phone': mock_user.get('phone') or '',
                'designation': mock_user.get('designation') or '',
                'department_name': mock_user.get('department_name') or '',
                'gender': mock_user.get('gender') or '',
                'dob': dob_val,
                'joining_date': joining_date_val,
                'status': mock_user.get('status') or 'Active',
                'onboarding_complete': bool(mock_user.get('onboarding_complete', False))
            }
        )
    except Exception as db_err:
        logger.error(f"Failed to save SyncedEmployee: {db_err}")


@shared_task
def process_bitrix_webhook_task(data):
    from common.bitrix_client import BitrixClient
    from notifications.models import BitrixSyncLog, Notification
    from django.contrib.auth import get_user_model
    from audit_logs.signals import log_action
    import datetime
    
    logger.info(f"process_bitrix_webhook_task called with data: {data}")
    
    bitrix_id = None
    # 1. Check direct keys for ID (including crm.id as requested)
    for key in ['id', 'ID', 'bitrix_id', 'bitrix_user_id', 'crm.id']:
        if key in data:
            bitrix_id = data[key]
            break
            
    # 2. Check nested inside 'data' key
    if not bitrix_id and isinstance(data.get('data'), dict):
        nested_data = data['data']
        if isinstance(nested_data.get('FIELDS'), dict):
            fields = nested_data['FIELDS']
            for key in ['ID', 'id', 'crm.id']:
                if key in fields:
                    bitrix_id = fields[key]
                    break
        if not bitrix_id:
            for key in ['id', 'ID', 'bitrix_id', 'bitrix_user_id', 'crm.id']:
                if key in nested_data:
                    bitrix_id = nested_data[key]
                    break

    # 3. Check nested inside 'fields' key
    if not bitrix_id and isinstance(data.get('fields'), dict):
        fields = data['fields']
        for key in ['ID', 'id', 'crm.id']:
            if key in fields:
                bitrix_id = fields[key]
                break

    if bitrix_id:
        bitrix_id = str(bitrix_id)
        try:
            # Force refresh cache so the new user is definitely retrieved
            mock_user = BitrixClient.get_user_detail(bitrix_id, force_refresh=True)
            if mock_user:
                # Check if the employee is in the onboarding stage/period
                today = datetime.date.today()
                day_14_ago = today - datetime.timedelta(days=14)
                
                emp_joining_date = mock_user.get('joining_date')
                if isinstance(emp_joining_date, str):
                    try:
                        emp_joining_date = datetime.datetime.strptime(emp_joining_date, '%Y-%m-%d').date()
                    except Exception:
                        emp_joining_date = today
                
                is_onboarding = True
                if emp_joining_date:
                    if emp_joining_date <= day_14_ago or mock_user.get('status') == 'Exited':
                        is_onboarding = False
                        
                if not is_onboarding:
                    logger.info(f"Employee {bitrix_id} is not in onboarding period. Ignored.")
                    return f"Ignored: Employee {bitrix_id} is not in onboarding."

                # Log success in BitrixSyncLog
                try:
                    BitrixSyncLog.objects.create(
                        employee_id=bitrix_id,
                        employee_name=mock_user.get('name') or f"Bitrix User {bitrix_id}",
                        action_type='Webhook Sync',
                        status='SUCCESS',
                        retry_count=0
                    )
                except Exception as log_err:
                    logger.error(f"Failed to create BitrixSyncLog: {log_err}")

                # Save to database
                save_synced_employee_to_db(mock_user)

                # Trigger welcome email task only if joining date and email are present
                emp_joining_date = mock_user.get('joining_date')
                emp_email = mock_user.get('email') or mock_user.get('work_email') or mock_user.get('personal_email')
                if emp_joining_date and emp_email:
                    try:
                        send_onboarding_welcome_email.delay(mock_user)
                    except Exception as mail_err:
                        logger.error(f"Failed to queue welcome email task: {mail_err}")
                else:
                    logger.info(f"Skipping automatic welcome email for employee {bitrix_id} because details (joining date or email) are missing.")

                # Trigger Admin Notification
                try:
                    User = get_user_model()
                    admins = User.objects.filter(role__code='ADMIN')
                    notif_msg = f"New employee synced from Bitrix24 – {mock_user.get('name')} ({mock_user.get('emp_id')})"
                    for admin in admins:
                        Notification.objects.create(
                            recipient=admin,
                            notif_type='INFO',
                            message=notif_msg,
                            link=f"/employees/{mock_user.get('id')}/"
                        )
                except Exception as notif_err:
                    logger.error(f"Failed to trigger Admin notification: {notif_err}")

                # Write to audit logs
                try:
                    log_action(None, "CREATE", "Onboarding", f"Bitrix24 Webhook synced employee (ID: {bitrix_id}).")
                except Exception as audit_err:
                    logger.error(f"Failed to write audit log: {audit_err}")

                return f"Success: Employee {bitrix_id} synced."
            else:
                # Log failure in BitrixSyncLog
                try:
                    BitrixSyncLog.objects.create(
                        employee_id=bitrix_id,
                        employee_name=f"Bitrix User {bitrix_id}",
                        action_type='Webhook Sync',
                        status='FAILED',
                        retry_count=0,
                        error_message=f"Employee with ID {bitrix_id} not found in Bitrix24."
                    )
                    
                    # Notify Admin
                    User = get_user_model()
                    admins = User.objects.filter(role__code='ADMIN')
                    notif_msg = f"Bitrix24 sync failed for ID {bitrix_id} (Employee not found)."
                    for admin in admins:
                        Notification.objects.create(
                            recipient=admin,
                            notif_type='ERROR',
                            message=notif_msg,
                            link="/admin/bitrix/sync-log/"
                        )
                except Exception as err:
                    logger.error(f"Error handling webhook failure log/notification: {err}")
                return f"Failed: Employee with ID {bitrix_id} not found in Bitrix24."
        except Exception as e:
            try:
                BitrixSyncLog.objects.create(
                    employee_id=bitrix_id,
                    action_type='Webhook Sync',
                    status='FAILED',
                    retry_count=0,
                    error_message=str(e)
                )
            except Exception:
                pass
            logger.error(f"Exception syncing employee {bitrix_id} via webhook: {e}")
            return f"Error: {str(e)}"

    # Check if direct fields are provided (case 2)
    first_name = data.get('first_name') or data.get('name')
    email = data.get('email') or data.get('work_email')
    
    if first_name and email:
        webhook = BitrixClient.get_webhook_url()
        gender_code = 'M'
        gender_val = data.get('gender')
        if gender_val in ['FEMALE', 'Female']:
            gender_code = 'F'
        elif gender_val in ['OTHER', 'Other']:
            gender_code = 'O'

        dept_list = [1]
        if data.get('department'):
            try:
                dept_list = [int(data.get('department'))]
            except (ValueError, TypeError):
                pass

        user_payload = {
            'EMAIL': email,
            'NAME': first_name,
            'LAST_NAME': data.get('last_name') or '',
            'PERSONAL_MOBILE': data.get('phone') or '',
            'WORK_POSITION': data.get('designation') or 'Software Engineer',
            'UF_DEPARTMENT': dept_list,
            'PERSONAL_BIRTHDAY': data.get('dob') or '',
            'PERSONAL_GENDER': gender_code,
            'UF_PERSONAL_EMAIL': data.get('personal_email') or '',
            'PERSONAL_MAILBOX': data.get('personal_email') or ''
        }
        
        try:
            # Attempt to create as user profile first
            res = requests.post(f"{webhook}/user.add.json", json=user_payload, timeout=10)
            
            # Fallback to CRM contact creation if user scope fails or fails otherwise
            if not res.ok:
                emails = [{'VALUE': email, 'VALUE_TYPE': 'WORK'}]
                if data.get('personal_email'):
                    emails.append({'VALUE': data.get('personal_email'), 'VALUE_TYPE': 'HOME'})
                    
                crm_payload = {
                    'fields': {
                        'NAME': first_name,
                        'LAST_NAME': data.get('last_name') or '',
                        'EMAIL': emails,
                        'PHONE': [{'VALUE': data.get('phone') or '', 'VALUE_TYPE': 'WORK'}],
                        'POST': data.get('designation') or 'Software Engineer',
                        'UF_ONBOARDING_STATUS': 'Pending',
                        'UF_CRM_ONBOARDING_STATUS': 'Pending',
                        'UF_PERSONAL_EMAIL': data.get('personal_email') or '',
                        'PERSONAL_MAILBOX': data.get('personal_email') or ''
                    }
                }
                res = requests.post(f"{webhook}/crm.contact.add", json=crm_payload, timeout=10)
                
            if res.ok:
                contact_id = str(res.json().get('result'))
                BitrixClient.get_all_users(force_refresh=True)
                mock_user = BitrixClient.get_user_detail(contact_id)
                
                # Try to link to a local employee if we have a match
                from .models import SyncedEmployee
                from employee_onboarding.models import EmployeeDocument
                from salary.models import SalaryStructure, EmployeeBankDetail
                
                local_emp = None
                local_id = data.get('local_id') or data.get('crmID') or data.get('crmId')
                if local_id:
                    if not str(local_id).startswith('LOCAL-'):
                        local_emp = SyncedEmployee.objects.filter(bitrix_user_id=f"LOCAL-{local_id}").first()
                    if not local_emp:
                        local_emp = SyncedEmployee.objects.filter(bitrix_user_id=str(local_id)).first()
                        
                if not local_emp and email:
                    local_emp = SyncedEmployee.objects.filter(email__iexact=email, bitrix_user_id__startswith='LOCAL-').first()
                    if not local_emp:
                        local_emp = SyncedEmployee.objects.filter(email__iexact=email).first()

                if local_emp and local_emp.bitrix_user_id != contact_id:
                    old_local_id = local_emp.bitrix_user_id
                    
                    # Update references in all tables
                    EmployeeDocument.objects.filter(bitrix_user_id=old_local_id).update(bitrix_user_id=contact_id)
                    SalaryStructure.objects.filter(bitrix_user_id=old_local_id).update(bitrix_user_id=contact_id)
                    EmployeeBankDetail.objects.filter(bitrix_user_id=old_local_id).update(bitrix_user_id=contact_id)
                    
                    # Update local employee
                    local_emp.bitrix_user_id = contact_id
                    local_emp.bitrix_sync_status = 'Synced'
                    local_emp.bitrix_sync_error = None
                    local_emp.save()
                    
                    logger.info(f"Linked local employee {old_local_id} to new Bitrix ID {contact_id}")
                
                # Log success in BitrixSyncLog
                try:
                    BitrixSyncLog.objects.create(
                        employee_id=contact_id,
                        employee_name=mock_user.get('name') if mock_user else f"{first_name} {data.get('last_name', '')}".strip(),
                        action_type='Contact Create',
                        status='SUCCESS',
                        retry_count=0
                    )
                except Exception:
                    pass

                # Save to database
                save_synced_employee_to_db(mock_user)

                # Trigger welcome email task
                try:
                    send_onboarding_welcome_email.delay(mock_user)
                except Exception as mail_err:
                    logger.error(f"Failed to queue welcome email task: {mail_err}")
                
                # Trigger Admin Notification
                try:
                    User = get_user_model()
                    admins = User.objects.filter(role__code='ADMIN')
                    notif_msg = f"New employee added via Webhook – {mock_user.get('name')} ({mock_user.get('emp_id')})"
                    for admin in admins:
                        Notification.objects.create(
                            recipient=admin,
                            notif_type='INFO',
                            message=notif_msg,
                            link=f"/employees/{mock_user.get('id')}/"
                        )
                except Exception as notif_err:
                    logger.error(f"Failed to trigger Admin notification: {notif_err}")

                # Write to audit logs
                try:
                    log_action(None, "CREATE", "Onboarding", f"Bitrix24 Webhook created employee (ID: {contact_id}).")
                except Exception:
                    pass

                return f"Success: Contact {contact_id} created and synced."
            else:
                # Log failure in BitrixSyncLog
                emp_name = f"{first_name} {data.get('last_name', '')}".strip()
                try:
                    BitrixSyncLog.objects.create(
                        employee_name=emp_name,
                        action_type='Contact Create',
                        status='FAILED',
                        retry_count=0,
                        error_message=res.text
                    )
                    
                    # Notify Admin
                    User = get_user_model()
                    admins = User.objects.filter(role__code='ADMIN')
                    notif_msg = f"Bitrix24 webhook sync failed for {emp_name} (Contact Create). Retry available."
                    for admin in admins:
                        Notification.objects.create(
                            recipient=admin,
                            notif_type='ERROR',
                            message=notif_msg,
                            link="/admin/bitrix/sync-log/"
                        )
                except Exception:
                    pass

                # Save local entry anyway (with TEMP- prefix) so data shows up in DB during local/restricted token testing
                try:
                    from .models import SyncedEmployee
                    def parse_date_str(val):
                        if not val:
                            return None
                        if isinstance(val, (datetime.date, datetime.datetime)):
                            return val.date() if isinstance(val, datetime.datetime) else val
                        try:
                            return datetime.datetime.strptime(str(val).strip(), '%Y-%m-%d').date()
                        except Exception:
                            return None
                    
                    dob_val = parse_date_str(data.get('dob'))
                    joining_date_val = parse_date_str(data.get('joining_date'))
                    
                    SyncedEmployee.objects.update_or_create(
                        bitrix_user_id=f"TEMP-{email}",
                        defaults={
                            'first_name': first_name,
                            'last_name': data.get('last_name') or '',
                            'email': email,
                            'phone': data.get('phone') or '',
                            'designation': data.get('designation') or '',
                            'department_name': data.get('department') or '',
                            'gender': data.get('gender') or '',
                            'dob': dob_val,
                            'joining_date': joining_date_val,
                            'status': 'Active',
                            'onboarding_complete': False
                        }
                    )
                except Exception as local_db_err:
                    logger.error(f"Failed to save fallback SyncedEmployee: {local_db_err}")

                return f"Failed to create employee contact in Bitrix24: {res.text}"
        except Exception as e:
            logger.error(f"Exception creating employee contact via webhook: {e}")
            return f"Error: {str(e)}"
            
    return "Error: Missing ID or required fields."
