# apps/notifications/tasks.py
import datetime
import logging
import requests
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.contrib.auth import get_user_model
from django.utils import timezone
from common.bitrix_client import BitrixClient, BitrixEmployeeMock
from salary.models import SalaryIncrementReminder, SalaryIncrementApproval
from exit_formality.models import ExitSecureLink, ExitRequest
from .models import Notification, BitrixSyncLog

User = get_user_model()
logger = logging.getLogger(__name__)

@shared_task
def check_onboarding_status():
    """
    Daily check running at 08:00 (Trigger 5 and 6)
    """
    logger.info("Running check_onboarding_status daily pipeline...")
    today = datetime.date.today()
    active_users = BitrixClient.get_all_users()
    active_employees = [BitrixEmployeeMock(u) for u in active_users]
    
    admins_and_hrs = User.objects.filter(role__code__in=['ADMIN', 'HR'])
    
    # Trigger 5: Onboarding Ending Tomorrow (Day 14)
    # today = joining_date + 14 days
    day_14_ago = today - datetime.timedelta(days=14)
    for emp in active_employees:
        if emp.joining_date == day_14_ago and emp.status != 'Exited':
            msg = f"{emp.name}'s onboarding period ends tomorrow. Ensure all docs are uploaded."
            for user in admins_and_hrs:
                Notification.objects.create(
                    recipient=user,
                    notif_type='INFO',
                    message=msg,
                    link=f"/employees/{emp.id}/"
                )

    # Trigger 6: Employee Graduated (Day 16)
    # today == joining_date + 16 days
    day_16_ago = today - datetime.timedelta(days=16)
    for emp in active_employees:
        if emp.joining_date == day_16_ago and emp.status != 'Exited':
            msg = f"{emp.name} has completed onboarding and moved to All Employees"
            for user in admins_and_hrs:
                Notification.objects.create(
                    recipient=user,
                    notif_type='SUCCESS',
                    message=msg,
                    link=f"/employees/{emp.id}/"
                )
            
            # Employee gets email
            recipient_email = emp.personal_email or emp.work_email or emp.email
            if recipient_email:
                try:
                    subject = "Onboarding Complete – Welcome to the MTLV Team"
                    body = f"""Dear {emp.first_name},

Congratulations! You have successfully completed your onboarding period at MTLV.

Your details have been moved to the All Employees directory, and your salary has been activated.

We are excited to have you as a full member of our team and wish you a successful career ahead.

Best Regards,
HR Team
MTLV
"""
                    send_mail(
                        subject=subject,
                        message=body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient_email],
                        fail_silently=True
                    )
                except Exception as e:
                    logger.error(f"Failed to send graduation email to {recipient_email}: {e}")


@shared_task
def check_salary_structure_missing():
    """
    Trigger 2: Salary structure missing (3 days post joining)
    """
    logger.info("Running check_salary_structure_missing...")
    today = datetime.date.today()
    active_users = BitrixClient.get_all_users()
    active_employees = [BitrixEmployeeMock(u) for u in active_users]
    
    admins = User.objects.filter(role__code='ADMIN')
    hrs = User.objects.filter(role__code='HR')
    
    from salary.models import SalaryStructure
    
    joined_3_days_ago = today - datetime.timedelta(days=3)
    for emp in active_employees:
        if emp.joining_date == joined_3_days_ago and emp.status != 'Exited':
            if not SalaryStructure.objects.filter(bitrix_user_id=emp.bitrix_id).exists():
                msg = f"Salary structure not set for {emp.name} (joined 3 days ago). Please configure it."
                
                # HR gets In-app + Email
                for hr in hrs:
                    Notification.objects.create(
                        recipient=hr,
                        notif_type='WARNING',
                        message=msg,
                        link=f"/employees/{emp.id}/salary/"
                    )
                    if hr.email:
                        send_mail(
                            subject=f"Salary Structure Missing – {emp.name}",
                            message=f"{msg}\n\nPlease configure it at {settings.FRONTEND_URL}/employees/{emp.id}/salary/.",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[hr.email],
                            fail_silently=True
                        )
                # Admin gets In-app only
                for admin in admins:
                    Notification.objects.create(
                        recipient=admin,
                        notif_type='WARNING',
                        message=msg,
                        link=f"/employees/{emp.id}/salary/"
                    )


@shared_task
def check_document_completion():
    """
    Trigger 3: Documents incomplete (5 days post joining)
    """
    logger.info("Running check_document_completion...")
    today = datetime.date.today()
    active_users = BitrixClient.get_all_users()
    active_employees = [BitrixEmployeeMock(u) for u in active_users]
    
    hrs = User.objects.filter(role__code='HR')
    from employee_onboarding.models import EmployeeDocument
    
    joined_5_days_ago = today - datetime.timedelta(days=5)
    for emp in active_employees:
        if emp.joining_date == joined_5_days_ago and emp.status != 'Exited':
            uploaded_docs = set(EmployeeDocument.objects.filter(bitrix_user_id=emp.bitrix_id).values_list('doc_type', flat=True))
            
            missing_docs = []
            if 'AADHAAR' not in uploaded_docs:
                missing_docs.append("Aadhaar")
            if 'PAN' not in uploaded_docs:
                missing_docs.append("PAN")
                
            if missing_docs:
                missing_str = ", ".join(missing_docs)
                msg = f"Documents pending for {emp.name} – {missing_str} not uploaded"
                
                # HR gets in-app only
                for hr in hrs:
                    Notification.objects.create(
                        recipient=hr,
                        notif_type='WARNING',
                        message=msg,
                        link=f"/employees/{emp.id}/documents/"
                    )
                
                # Employee gets email only
                recipient_email = emp.personal_email or emp.work_email or emp.email
                if recipient_email:
                    subject = "Reminder: Pending Documents – MTLV HR"
                    missing_docs_str = "\n".join(f"- {d}" for d in missing_docs)
                    body = f"""Dear {emp.first_name},

This is a reminder that the following required documents are pending to complete your onboarding formalities at MTLV:
{missing_docs_str}

Please upload them via the employee portal or submit them to the HR team.

Best Regards,
HR Team
MTLV
"""
                    send_mail(
                        subject=subject,
                        message=body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient_email],
                        fail_silently=True
                    )


@shared_task
def check_salary_increment_reminders():
    """
    Triggers 7, 8, 9: Salary Increment Reviews
    Runs daily at 08:00
    """
    logger.info("Running check_salary_increment_reminders...")
    today = datetime.date.today()
    active_users = BitrixClient.get_all_users()
    active_employees = [BitrixEmployeeMock(u) for u in active_users]
    
    admins = User.objects.filter(role__code='ADMIN')
    hrs = User.objects.filter(role__code='HR')
    
    for emp in active_employees:
        if not emp.joining_date:
            continue
        
        anniversary_date = emp.joining_date + datetime.timedelta(days=365)
        diff_days = (anniversary_date - today).days
        
        if diff_days in (15, 7, 0):
            reminder, created = SalaryIncrementReminder.objects.get_or_create(
                bitrix_user_id=emp.bitrix_id,
                anniversary_date=anniversary_date
            )
            
            if reminder.status == 'Actioned':
                continue
                
            trigger_reminder = False
            msg = ""
            level = "WARNING"
            subject = ""
            
            if diff_days == 15 and not reminder.reminder_15_sent:
                reminder.reminder_15_sent = True
                trigger_reminder = True
                level = "WARNING"
                msg = f"Salary review due in 15 days – {emp.name} Anniversary: {anniversary_date.strftime('%d %b %Y')}"
                subject = f"Salary Increment Due in 15 Days – {emp.name}"
            elif diff_days == 7 and not reminder.reminder_7_sent:
                reminder.reminder_7_sent = True
                trigger_reminder = True
                level = "WARNING"
                msg = f"REMINDER: Salary review due in 7 days – {emp.name}"
                subject = f"REMINDER: Salary review due in 7 days – {emp.name}"
            elif diff_days == 0 and not reminder.reminder_0_sent:
                reminder.reminder_0_sent = True
                trigger_reminder = True
                level = "URGENT"
                msg = f"ACTION REQUIRED TODAY: Salary review due – {emp.name}'s 1-year anniversary is today"
                subject = f"URGENT: Salary Increment Due Today – {emp.name}"
                
            if trigger_reminder:
                reminder.save()
                
                from salary.models import SalaryStructure
                struct = SalaryStructure.objects.filter(bitrix_user_id=emp.bitrix_id).order_by('-effective_from').first()
                curr_salary = f"Rs. {struct.net_salary:,.2f}" if struct else "Not configured"
                
                body = f"""Dear Team,

This is to notify you that a salary review is due for:
- Employee: {emp.name}
- Department: {emp.department_name}
- Designation: {emp.designation}
- Joining Date: {emp.joining_date}
- Anniversary Date: {anniversary_date}
- Current Net Salary: {curr_salary}

Admin Link to Increment Approval Form: {settings.FRONTEND_URL}/increment/{emp.id}/
"""
                email_recipients = [u.email for u in list(admins) + list(hrs) if u.email]
                if email_recipients:
                    send_mail(
                        subject=subject,
                        message=body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=email_recipients,
                        fail_silently=True
                    )
                
                for user in list(admins) + list(hrs):
                    Notification.objects.create(
                        recipient=user,
                        notif_type=level,
                        message=msg,
                        link=f"/increment/{emp.id}/"
                    )


@shared_task
def check_expiring_exit_links():
    """
    Trigger 14: warning on exit links expiring in 24 hours
    """
    logger.info("Running check_expiring_exit_links...")
    now_dt = timezone.now()
    expiring_soon = ExitSecureLink.objects.filter(
        used=False,
        expires_at__gt=now_dt,
        expires_at__lte=now_dt + datetime.timedelta(days=1)
    )
    
    admins = User.objects.filter(role__code='ADMIN')
    hrs = User.objects.filter(role__code='HR')
    
    for link in expiring_soon:
        exit_req = link.exit_request
        emp = exit_req.employee
        msg = f"Exit form link expiring in 24 hours – {emp.name}. Resend if employee has not submitted yet."
        
        # HR gets in-app + Email
        for hr in hrs:
            Notification.objects.create(
                recipient=hr,
                notif_type='WARNING',
                message=msg,
                link=f"/exit/{emp.id}/"
            )
            if hr.email:
                send_mail(
                    subject=f"Exit Link Expiring Soon – {emp.name}",
                    message=f"{msg}\n\nView details at {settings.FRONTEND_URL}/exit/{emp.id}/.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[hr.email],
                    fail_silently=True
                )
                
        # Admin gets in-app only
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type='WARNING',
                message=msg,
                link=f"/exit/{emp.id}/"
            )


@shared_task
def retry_failed_bitrix_syncs():
    """
    Trigger 25: retry failed bitrix syncs and handle permanent failure
    Runs daily at 09:00
    """
    logger.info("Running retry_failed_bitrix_syncs...")
    failed_logs = BitrixSyncLog.objects.filter(status='FAILED')
    webhook = BitrixClient.get_webhook_url()
    
    for log in failed_logs:
        log.retry_count += 1
        success = False
        error_msg = ""
        
        try:
            # Re-fetch or retry depending on action type
            res = requests.post(f"{webhook}/user.get.json", json={'ID': log.employee_id or '0'}, timeout=10)
            if res.ok:
                success = True
            else:
                error_msg = f"API Error: {res.text}"
        except Exception as err:
            error_msg = str(err)
            
        if success:
            log.status = 'SUCCESS'
            log.save()
        else:
            log.error_message = error_msg
            if log.retry_count >= 3:
                log.status = 'PERMANENTLY_FAILED'
                log.save()
                
                admins = User.objects.filter(role__code='ADMIN')
                notif_msg = f"Bitrix24 sync permanently failed for {log.employee_name} after 3 retries. Manual action required."
                
                for admin in admins:
                    Notification.objects.create(
                        recipient=admin,
                        notif_type='ERROR',
                        message=notif_msg,
                        link="/admin/bitrix/sync-log/"
                    )
                    
                    if admin.email:
                        send_mail(
                            subject=f"URGENT: Bitrix24 Sync Permanently Failed – {log.employee_name}",
                            message=f"{notif_msg}\n\nPlease review sync logs at {settings.FRONTEND_URL}/admin/bitrix/sync-log/.",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[admin.email],
                            fail_silently=True
                        )
            else:
                log.save()


@shared_task
def send_increment_letter(approval_id):
    """
    Trigger 10: Increment approved by Admin
    """
    try:
        approval = SalaryIncrementApproval.objects.get(id=approval_id)
        emp = approval.employee
        admin = approval.approved_by
    except SalaryIncrementApproval.DoesNotExist:
        return "Approval record not found."
        
    admin_name = f"{admin.first_name} {admin.last_name}".strip() if admin else "Admin"
    if not admin_name:
        admin_name = admin.username if admin else "Admin"
        
    effective_str = approval.effective_date.strftime('%d %b %Y')
    new_net_formatted = f"{approval.new_net:,.0f}"
    
    # Notify HR (In-app + Email)
    hrs = User.objects.filter(role__code='HR')
    msg = f"Salary increment approved for {emp.name} by Admin {admin_name}. New Net: ₹{new_net_formatted}. Effective: {effective_str}"
    
    for hr in hrs:
        Notification.objects.create(
            recipient=hr,
            notif_type='SUCCESS',
            message=msg,
            link=f"/increment/{emp.id}/"
        )
        if hr.email:
            send_mail(
                subject=f"Salary Increment Approved – {emp.name}",
                message=f"{msg}\n\nView details at {settings.FRONTEND_URL}/increment/{emp.id}/.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[hr.email],
                fail_silently=True
            )
            
    # Email employee with attached PDF
    recipient_email = emp.personal_email or emp.work_email or emp.email
    if recipient_email:
        subject = f"Your Salary has been Revised – Effective {effective_str}"
        body = f"""Dear {emp.first_name},

Please find attached your official salary revision and increment letter effective from {effective_str}.

If you have any questions, feel free to reach out to the HR department.

Best Regards,
HR Team
MTLV
"""
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient_email]
        )
        if approval.pdf_file:
            try:
                email.attach(f"Increment_Letter_{emp.first_name}.pdf", approval.pdf_file.read(), 'application/pdf')
            except Exception as e:
                logger.error(f"Failed to read/attach increment PDF: {e}")
                
        try:
            email.send(fail_silently=False)
        except Exception as e:
            logger.error(f"Failed to send increment letter email to {recipient_email}: {e}")
            
    # Mark reminders for this employee as read / actioned
    Notification.objects.filter(link__icontains=f"/increment/{emp.id}/", is_read=False).update(is_read=True)
    return "Increment notifications and letter dispatched."


@shared_task
def send_certificate_email(student_id):
    """
    Trigger 23 (Manual): Send generated certificate to student
    """
    from student_certificate.models import Student
    try:
        student = Student.objects.get(id=student_id)
    except Student.DoesNotExist:
        return "Student not found."
        
    recipient_email = student.email
    if not recipient_email:
        return "No email for student."
        
    subject = f"Your Internship Certificate – MTLV"
    if student.cert_type == 'TRAINING_CERT':
        subject = f"Your Training Completion Certificate – MTLV"
    elif student.cert_type == 'PROJECT_CERT':
        subject = f"Your Project Completion Certificate – MTLV"
        
    body = f"""Dear {student.name},

Please find attached your completion certificate for the {student.program_name} program at MTLV.

We appreciate your hard work and dedication, and wish you all the best in your future endeavors.

Best Regards,
HR Team
MTLV
"""
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email]
    )
    if student.cert_pdf:
        try:
            email.attach(f"Certificate_{student.name.replace(' ', '_')}.pdf", student.cert_pdf.read(), 'application/pdf')
        except Exception as e:
            logger.error(f"Failed to read/attach certificate PDF: {e}")
            
    try:
        email.send(fail_silently=False)
    except Exception as e:
        logger.error(f"Failed to send certificate email to {recipient_email}: {e}")
        return f"Failed: {e}"
        
    return "Certificate email sent successfully."


@shared_task
def run_daily_onboarding_pipeline():
    """
    Combined beat task running at 08:00
    """
    check_onboarding_status()
    check_salary_structure_missing()
    check_document_completion()
    check_salary_increment_reminders()
    check_expiring_exit_links()
    return "Onboarding pipeline execution complete."
