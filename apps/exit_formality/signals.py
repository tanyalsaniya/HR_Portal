import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import ExitRequest, ExitFormResponse

@receiver(post_save, sender=ExitFormResponse)
def exit_form_response_post_save(sender, instance, created, **kwargs):
    """
    When the questionnaire is submitted:
    If the ExitRequest status is NOT already 'OVERRIDDEN', 'CANCELLED', or 'FULLY_EXITED',
    auto-update the status to 'COMPLETED'.
    """
    if instance.declaration_confirmed:
        exit_req = instance.exit_request
        if exit_req.status not in ('OVERRIDDEN', 'CANCELLED', 'FULLY_EXITED'):
            exit_req.status = 'COMPLETED'
            exit_req.save(update_fields=['status'])

@receiver(post_save, sender=ExitRequest)
def exit_request_post_save(sender, instance, created, **kwargs):
    """
    When ExitRequest status is updated to FULLY_EXITED:
    1. Trigger async Bitrix24 status update & PDF attachments
    2. Trigger Celery task to email all final documents
    """
    if not created and instance.status == 'FULLY_EXITED':
        # Trigger Celery task to update Bitrix24 and send documents
        from .tasks import update_bitrix24_on_exit, send_exit_documents_after_fully_exited
        update_bitrix24_on_exit.delay(instance.id)
        if instance.send_email_on_exit:
            send_exit_documents_after_fully_exited.delay(instance.id)
