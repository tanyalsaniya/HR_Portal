from django.db import models
from django.conf import settings
from rules import (
    GENDER_CHOICES, EMPLOYMENT_TYPE_CHOICES, EMERGENCY_RELATION_CHOICES,
    INDIAN_STATES, VALID_DOC_TYPES
)
from common.fields import EncryptedCharField
from common.utils import generate_employee_id

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

def upload_to_uuid_filename(instance, filename):
    import uuid
    import os
    ext = os.path.splitext(filename)[1].lower()
    uuid_filename = f"{uuid.uuid4()}{ext}"
    return f"employees/{instance.bitrix_user_id}/docs/{uuid_filename}"

class EmployeeDocument(models.Model):
    bitrix_user_id = models.CharField(max_length=50, db_index=True, null=True, blank=True)
    doc_type = models.CharField(max_length=30, choices=VALID_DOC_TYPES)
    label = models.CharField(max_length=100, blank=True, null=True)
    file = models.FileField(upload_to=upload_to_uuid_filename)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )

    def save(self, *args, **kwargs):
        if not self.original_filename and self.file:
            import os
            self.original_filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"User {self.bitrix_user_id} - {self.get_doc_type_display()}"


class LetterTemplate(models.Model):
    TEMPLATE_CHOICES = (
        ('OFFER_LETTER', 'Offer Letter'),
        ('APPOINTMENT_LETTER', 'Appointment Letter'),
        ('BOND_LETTER', 'Bond Letter'),
        ('RELIEVING_LETTER', 'Relieving Letter'),
        ('EXPERIENCE_LETTER', 'Experience Letter'),
        ('NOTICE_LETTER', 'Notice Period Letter'),
        ('NOC_LETTER', 'NOC Letter'),
        ('FF_SETTLEMENT_LETTER', 'F&F Settlement Letter'),
        ('FF_SALARY_SLIP', 'Final Month Payslip'),
    )
    name = models.CharField(max_length=30, choices=TEMPLATE_CHOICES, unique=True)
    title = models.CharField(max_length=100)
    html_content = models.TextField()
    allow_hr_edit = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

