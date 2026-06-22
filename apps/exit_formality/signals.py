# apps/exit_formality/signals.py
import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from notifications.models import Notification
from .models import ExitRequest, ExitFormResponse, ExitFFSettlement

User = get_user_model()

@receiver(post_save, sender=ExitFormResponse)
def exit_form_response_post_save(sender, instance, created, **kwargs):
    """
    Trigger 15: When exit form is submitted, update status to COMPLETED and queue notifications.
    """
    if instance.declaration_confirmed:
        exit_req = instance.exit_request
        if exit_req.status not in ('OVERRIDDEN', 'CANCELLED', 'FULLY_EXITED'):
            exit_req.status = 'COMPLETED'
            exit_req.save(update_fields=['status'])
        
        # Trigger Celery task for employee confirmation and HR/Admin notifications
        from .tasks import send_exit_form_submission_notification
        send_exit_form_submission_notification.delay(instance.id)


@receiver(post_save, sender=ExitRequest)
def exit_request_post_save(sender, instance, created, **kwargs):
    """
    Handles exit process triggers:
    - Trigger 11: Exit initiated by HR (secure link emailed to employee, Admin gets in-app)
    - Trigger 12: Absconding exit initiated (Admin gets in-app + email, no secure link)
    - Trigger 16: All clearances done (Admin gets in-app + email)
    - Trigger 19: Employee marked fully exited (Admin gets in-app, final docs emailed to employee personal email)
    """
    emp = instance.employee
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8000')
    
    if created:
        if instance.exit_type == 'ABSCONDING':
            # Trigger 12: Absconding exit
            # Admin gets in-app + Email (URGENT)
            admins = User.objects.filter(role__code='ADMIN')
            msg = f"Absconding exit initiated for {emp.name}. Admin override required. No secure link will be sent."
            
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    notif_type='URGENT',
                    message=msg,
                    link=f"/exit/{instance.id}/"
                )
                if admin.email:
                    send_mail(
                        subject=f"URGENT: Absconding Exit – {emp.name}",
                        message=f"{msg}\n\nReview at {frontend_url}/exit/{instance.id}/.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[admin.email],
                        fail_silently=True
                    )
        else:
            # Trigger 11: Routine exit initiation
            # Admin gets in-app only (INFO)
            admins = User.objects.filter(role__code='ADMIN')
            hr_name = f"{instance.initiated_by.first_name} {instance.initiated_by.last_name}".strip() if instance.initiated_by else "HR"
            if not hr_name and instance.initiated_by:
                hr_name = instance.initiated_by.username
                
            msg = f"Exit process initiated for {emp.name} LWD: {instance.last_working_day.strftime('%d %b %Y')} by HR {hr_name}"
            
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    notif_type='INFO',
                    message=msg,
                    link=f"/exit/{instance.id}/"
                )
                
            # Queue Celery task to email secure link to employee
            from .tasks import send_exit_initiation_email
            send_exit_initiation_email.delay(instance.id)

    else:
        # Update cases
        if instance.status == 'FULLY_EXITED':
            # Trigger 19: Fully Exited
            # Admin gets in-app only (INFO)
            admins = User.objects.filter(role__code='ADMIN')
            msg = f"{emp.name} has been fully exited from the system. All documents have been sent to their personal email."
            
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    notif_type='INFO',
                    message=msg,
                    link=f"/exit/{instance.id}/"
                )
                
            # Trigger async Bitrix24 status update & final documents emailing
            from .tasks import update_bitrix24_on_exit, send_exit_documents_after_fully_exited
            update_bitrix24_on_exit.delay(instance.id)
            if instance.send_email_on_exit:
                send_exit_documents_after_fully_exited.delay(instance.id)

        elif instance.status == 'CLEARANCES_DONE':
            # Trigger 16: Clearances completed
            # Admin gets in-app + Email (SUCCESS)
            admins = User.objects.filter(role__code='ADMIN')
            msg = f"All clearances complete for {emp.name}. Ready for F&F settlement."
            
            for admin in admins:
                Notification.objects.create(
                    recipient=admin,
                    notif_type='SUCCESS',
                    message=msg,
                    link=f"/exit/{instance.id}/ff/"
                )
                if admin.email:
                    send_mail(
                        subject=f"All Clearances Complete – {emp.name}",
                        message=f"{msg}\n\nView and calculate F&F at {frontend_url}/exit/{instance.id}/ff/.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[admin.email],
                        fail_silently=True
                    )


@receiver(post_save, sender=ExitFFSettlement)
def exit_ff_settlement_post_save(sender, instance, created, **kwargs):
    """
    Handles F&F Settlement triggers:
    - Trigger 17: Calculation submitted by HR (Admin gets in-app + email)
    - Trigger 18: Approved by Admin (HR gets in-app + email)
    """
    exit_req = instance.exit_request
    emp = exit_req.employee
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8000')
    
    if created:
        # Trigger 17: F&F calculation submitted
        # Admin gets in-app + Email (WARNING)
        admins = User.objects.filter(role__code='ADMIN')
        hr_name = f"{instance.created_by.first_name} {instance.created_by.last_name}".strip() if instance.created_by else "HR"
        if not hr_name and instance.created_by:
            hr_name = instance.created_by.username
            
        msg = f"F&F calculation submitted for {emp.name} by HR {hr_name}. Net Payable: ₹{instance.net_payable:,.0f}. Awaiting your approval."
        
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notif_type='WARNING',
                message=msg,
                link=f"/exit/{exit_req.id}/ff/"
            )
            if admin.email:
                send_mail(
                    subject=f"F&F Calculation Submitted – {emp.name}",
                    message=f"{msg}\n\nReview and approve at {frontend_url}/exit/{exit_req.id}/ff/.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin.email],
                    fail_silently=True
                )
    else:
        # Trigger 18: Admin approves F&F
        if instance.approved_by and not getattr(instance, '_already_approved_notified', False):
            instance._already_approved_notified = True
            
            hrs = User.objects.filter(role__code='HR')
            admin_name = f"{instance.approved_by.first_name} {instance.approved_by.last_name}".strip() if instance.approved_by else "Admin"
            if not admin_name and instance.approved_by:
                admin_name = instance.approved_by.username
                
            msg = f"F&F approved for {emp.name} by Admin {admin_name}. Next: Mark as Fully Exited."
            
            for hr in hrs:
                Notification.objects.create(
                    recipient=hr,
                    notif_type='SUCCESS',
                    message=msg,
                    link=f"/exit/{exit_req.id}/"
                )
                if hr.email:
                    send_mail(
                        subject=f"F&F Approved – {emp.name}",
                        message=f"{msg}\n\nMark employee exited at {frontend_url}/exit/{exit_req.id}/.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[hr.email],
                        fail_silently=True
                    )
