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

class Employee(models.Model):
    STATUS_CHOICES = (
        ('Active', 'Active'),
        ('Exited', 'Exited'),
        ('Rejoined', 'Rejoined'),
    )

    emp_id = models.CharField(max_length=20, unique=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    alternate_phone = models.CharField(max_length=15, blank=True, null=True)
    dob = models.DateField()
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES)
    
    address_line1 = models.CharField(max_length=200)
    address_line2 = models.CharField(max_length=200, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=10, choices=INDIAN_STATES)
    pin_code = models.CharField(max_length=6)
    
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='employees')
    designation = models.CharField(max_length=100)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES)
    joining_date = models.DateField()
    exit_date = models.DateField(null=True, blank=True)
    notice_period_days = models.PositiveIntegerField(default=30)
    bond_period_months = models.PositiveIntegerField(default=0, blank=True)

    
    emergency_contact_name = models.CharField(max_length=100)
    emergency_relationship = models.CharField(max_length=20, choices=EMERGENCY_RELATION_CHOICES)
    emergency_phone = models.CharField(max_length=15)
    
    aadhaar_encrypted = EncryptedCharField(blank=True, null=True)
    pan_encrypted = EncryptedCharField(blank=True, null=True)
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    pan_no = models.CharField(max_length=20, blank=True, null=True)
    profile_photo = models.ImageField(upload_to='employees/profile_photos/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    is_deleted = models.BooleanField(default=False)
    onboarding_complete = models.BooleanField(default=False, db_index=True)
    bitrix_sync_status = models.CharField(
        max_length=20,
        choices=(('Synced', 'Synced'), ('Pending', 'Pending'), ('Failed', 'Failed')),
        default='Pending'
    )
    bitrix_contact_id = models.CharField(max_length=100, blank=True, null=True)
    bitrix_sync_error = models.TextField(blank=True, null=True)

    rejoined_from = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='tenures')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_employees'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.emp_id:
            # Generate employee ID using the joining year instead of today's year
            from django.apps import apps
            import datetime
            year = self.joining_date.year if self.joining_date else datetime.date.today().year
            prefix = f"EMP-{year}-"
            Employee = apps.get_model('employee_onboarding', 'Employee')
            last_emp = Employee.objects.filter(emp_id__startswith=prefix).order_by('-emp_id').first()
            if last_emp:
                try:
                    last_sequence = int(last_emp.emp_id.split('-')[-1])
                    new_sequence = last_sequence + 1
                except (ValueError, IndexError):
                    new_sequence = 1
            else:
                new_sequence = 1
            self.emp_id = f"{prefix}{new_sequence:04d}"
        super().save(*args, **kwargs)

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.emp_id})"

def upload_to_uuid_filename(instance, filename):
    import uuid
    import os
    ext = os.path.splitext(filename)[1].lower()
    uuid_filename = f"{uuid.uuid4()}{ext}"
    return f"employees/{instance.employee.emp_id}/docs/{uuid_filename}"

class EmployeeDocument(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
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
        return f"{self.employee.emp_id} - {self.get_doc_type_display()}"


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

