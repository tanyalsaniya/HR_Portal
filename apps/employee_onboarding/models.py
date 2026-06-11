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
    notice_period_days = models.PositiveIntegerField(default=30)
    bond_period_months = models.PositiveIntegerField(default=0, blank=True)
    
    emergency_contact_name = models.CharField(max_length=100)
    emergency_relationship = models.CharField(max_length=20, choices=EMERGENCY_RELATION_CHOICES)
    emergency_phone = models.CharField(max_length=15)
    
    aadhaar_encrypted = EncryptedCharField(blank=True, null=True)
    pan_encrypted = EncryptedCharField(blank=True, null=True)
    profile_photo = models.ImageField(upload_to='employees/profile_photos/', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    is_deleted = models.BooleanField(default=False)
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
            self.emp_id = generate_employee_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.emp_id})"

class EmployeeDocument(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=30, choices=VALID_DOC_TYPES)
    label = models.CharField(max_length=100, blank=True, null=True)
    file = models.FileField(upload_to='employees/documents/')
    upload_date = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )

    def __str__(self):
        return f"{self.employee.emp_id} - {self.get_doc_type_display()}"
