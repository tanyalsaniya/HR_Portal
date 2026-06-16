import os
import requests
import logging
import datetime
from celery import shared_task
from django.conf import settings
from .models import Employee, EmployeeDocument

logger = logging.getLogger(__name__)

def get_bitrix_webhook():
    return os.getenv('BITRIX24_WEBHOOK_URL')

@shared_task(bind=True, max_retries=3)
def sync_employee_to_bitrix24(self, employee_id):
    try:
        employee = Employee.objects.get(id=employee_id)
    except Employee.DoesNotExist:
        return f"Employee with ID {employee_id} not found."

    webhook = get_bitrix_webhook()
    if not webhook:
        employee.bitrix_sync_status = 'Failed'
        employee.bitrix_sync_error = "Bitrix24 webhook URL is not configured in .env"
        employee.save()
        return "Sync skipped: Bitrix24 webhook URL is not configured."

    employee.bitrix_sync_status = 'Pending'
    employee.save()

    # Search if Contact already exists or create/update
    try:
        contact_id = employee.bitrix_contact_id
        
        # If not set, check if we can find by email
        if not contact_id:
            search_url = f"{webhook.rstrip('/')}/crm.contact.list"
            search_payload = {
                'filter': {'EMAIL': employee.email},
                'select': ['ID']
            }
            try:
                res = requests.post(search_url, json=search_payload, timeout=10)
                if res.ok:
                    results = res.json().get('result', [])
                    if results:
                        contact_id = results[0]['ID']
                        employee.bitrix_contact_id = contact_id
            except Exception as e:
                logger.warning(f"Error searching Bitrix24 contacts: {e}")

        # Update or Create fields payload
        status_value = 'Completed' if employee.onboarding_complete else 'Pending'
        payload = {
            'fields': {
                'NAME': employee.first_name,
                'LAST_NAME': employee.last_name,
                'EMAIL': [{'VALUE': employee.email, 'VALUE_TYPE': 'WORK'}],
                'PHONE': [{'VALUE': employee.phone, 'VALUE_TYPE': 'WORK'}],
                'POST': employee.designation,
                'COMMENTS': f"Employee ID: {employee.emp_id}. Joined: {employee.joining_date}.",
                'UF_ONBOARDING_STATUS': status_value,
                'UF_CRM_ONBOARDING_STATUS': status_value
            }
        }

        if contact_id:
            update_url = f"{webhook.rstrip('/')}/crm.contact.update"
            payload['id'] = contact_id
            response = requests.post(update_url, json=payload, timeout=10)
            action = "updated"
        else:
            create_url = f"{webhook.rstrip('/')}/crm.contact.add"
            response = requests.post(create_url, json=payload, timeout=10)
            action = "created"

        if response.ok:
            result_data = response.json()
            if not contact_id:
                employee.bitrix_contact_id = str(result_data.get('result'))
            employee.bitrix_sync_status = 'Synced'
            employee.bitrix_sync_error = None
            employee.save()
            
            # Log audit event
            from audit_logs.signals import log_action
            log_action(None, "SYSTEM", employee, f"Bitrix24 contact {action} successfully (Contact ID: {employee.bitrix_contact_id}).")
            return f"Sync success: Contact {action}."
        else:
            raise Exception(f"Bitrix24 API returned error: {response.text}")
            
    except Exception as exc:
        logger.error(f"Bitrix24 sync error: {exc}")
        employee.bitrix_sync_status = 'Failed'
        employee.bitrix_sync_error = str(exc)
        employee.save()
        
        # Retry logic for network timeouts
        try:
            self.retry(exc=exc, countdown=60)
        except self.MaxRetriesExceededError:
            pass
            
        return f"Sync failed: {exc}"

@shared_task
def update_bitrix24_onboarding_status(employee_id):
    # Triggers CRM sync which updates status field values
    return sync_employee_to_bitrix24(employee_id)

@shared_task
def attach_document_to_bitrix24_timeline(document_id):
    try:
        doc = EmployeeDocument.objects.get(id=document_id)
        employee = doc.employee
    except EmployeeDocument.DoesNotExist:
        return "Document not found."

    webhook = get_bitrix_webhook()
    if not webhook or not employee.bitrix_contact_id:
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
                'OWNER_ID': employee.bitrix_contact_id,
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
