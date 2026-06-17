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
