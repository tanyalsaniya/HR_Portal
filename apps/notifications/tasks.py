# apps/notifications/tasks.py
import datetime
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from employee_onboarding.models import Employee
from salary.models import SalaryIncrementReminder
from student_certificate.models import StudentFeeInstallment
from student_certificate.services import send_fee_warning_email
from exit_formality.models import ExitSecureLink
from .models import Notification

User = get_user_model()

def check_upcoming_anniversaries():
    """
    Checks active employees for upcoming 1-year anniversaries (joining_date + 365 days).
    Sends notifications to all Admins and HRs 15 days, 7 days, and 0 days prior.
    Runs daily at 08:00 (called by Celery Beat or standard schedule runner).
    """
    print("Running check_upcoming_anniversaries task...")
    today = datetime.date.today()
    active_employees = Employee.objects.filter(status='Active', is_deleted=False)
    admins_and_hrs = User.objects.filter(role__in=('ADMIN', 'HR'))
    
    reminders_sent = 0
    for emp in active_employees:
        # Calculate anniversary date (usually 1 year of service)
        # Note: If they have multiple tenures, joining_date is the start date of the current tenure.
        anniversary_date = emp.joining_date + datetime.timedelta(days=365)
        diff_days = (anniversary_date - today).days
        
        if diff_days in (15, 7, 0):
            # Check if reminder already created for this cycle
            reminder, created = SalaryIncrementReminder.objects.get_or_create(
                employee=emp,
                anniversary_date=anniversary_date
            )
            
            # Skip if already actioned
            if reminder.status == 'Actioned':
                continue
                
            trigger_reminder = False
            msg = ""
            
            if diff_days == 15 and not reminder.reminder_15_sent:
                reminder.reminder_15_sent = True
                trigger_reminder = True
                msg = f"Salary Increment Review: {emp.first_name} {emp.last_name} completes 1 year of service in 15 days ({anniversary_date}). Action required."
            elif diff_days == 7 and not reminder.reminder_7_sent:
                reminder.reminder_7_sent = True
                trigger_reminder = True
                msg = f"Urgent Salary Increment Review: {emp.first_name} {emp.last_name} completes 1 year of service in 7 days ({anniversary_date}). Action required."
            elif diff_days == 0 and not reminder.reminder_0_sent:
                reminder.reminder_0_sent = True
                trigger_reminder = True
                msg = f"Anniversary Action Required Today: {emp.first_name} {emp.last_name} completes 1 year of service today ({anniversary_date}). Approve raise."
                
            if trigger_reminder:
                reminder.save()
                reminders_sent += 1
                
                # Send email notifications to Admins and HRs
                email_recipients = [u.email for u in admins_and_hrs if u.email]
                if email_recipients:
                    try:
                        send_mail(
                            subject=f"Anniversary Increment Warning: {emp.first_name} {emp.last_name}",
                            message=f"{msg}\n\nPlease log in to the HR Portal to approve or adjust their salary structure.",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=email_recipients,
                            fail_silently=True
                        )
                    except Exception as ex:
                        print(f"Error sending email: {ex}")
                
                # Send in-app bell notifications to Admins and HRs
                for user in admins_and_hrs:
                    Notification.objects.create(
                        recipient=user,
                        notif_type='WARNING' if diff_days > 0 else 'DANGER',
                        message=msg,
                        link=f"/salary/increments/?reminder_id={reminder.id}"
                    )
                    
    print(f"Anniversary check completed. Sent {reminders_sent} reminders.")
    return reminders_sent


def check_overdue_student_installments():
    """
    Checks for unpaid student fee installments due on or before today.
    Sends warning email to student, and notifies Admins.
    """
    print("Running check_overdue_student_installments task...")
    today = datetime.date.today()
    overdue_installments = StudentFeeInstallment.objects.filter(
        status__in=('UNPAID', 'PARTIALLY_PAID'),
        due_date__lte=today
    )
    
    admins = User.objects.filter(role__code='ADMIN')
    warnings_sent = 0
    
    for installment in overdue_installments:
        student = installment.student
        
        # Trigger email to student
        try:
            send_fee_warning_email(installment)
            warnings_sent += 1
        except Exception as ex:
            print(f"Error sending fee warning to student {student.name}: {ex}")
            
        # Create bell notification for Admins
        msg = f"Overdue Fee Installment: Student {student.name} installment {installment.installment_number} of Rs. {installment.amount} was due on {installment.due_date}."
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type='WARNING',
                message=msg,
                link=f"/students/{student.id}/installments/"
            )
            
    print(f"Overdue installment check completed. Sent {warnings_sent} student warnings.")
    return warnings_sent


def check_expiring_exit_links():
    """
    Checks for secure exit link UUIDs that are expiring in 24 hours (6 days after creation).
    Sends warning to HR/Admin.
    """
    print("Running check_expiring_exit_links task...")
    from django.utils import timezone
    now = timezone.now()
    
    # Links created between 6 and 7 days ago which are still not used
    expiring_soon = ExitSecureLink.objects.filter(
        used=False,
        expires_at__gt=now,
        expires_at__lte=now + datetime.timedelta(days=1)
    )
    
    admins_and_hrs = User.objects.filter(role__in=('ADMIN', 'HR'))
    notifs_sent = 0
    
    for link in expiring_soon:
        exit_req = link.exit_request
        employee = exit_req.employee
        msg = f"Exit Link Expiring Soon: Secure exit form link for {employee.first_name} {employee.last_name} expires in less than 24 hours. Resend link if needed."
        
        for user in admins_and_hrs:
            Notification.objects.create(
                recipient=user,
                notif_type='WARNING',
                message=msg,
                link=f"/exit/requests/{exit_req.id}/"
            )
        notifs_sent += 1
        
    print(f"Expiring links check completed. Logged warnings for {notifs_sent} requests.")
    return notifs_sent


def run_daily_checks():
    """
    Combines all scheduled checks to run as a single pipeline task.
    """
    check_upcoming_anniversaries()
    check_overdue_student_installments()
    check_expiring_exit_links()
