from django.db import models
from django.conf import settings
from decimal import Decimal
from rules import (
    STUDENT_TYPE_CHOICES, CERTIFICATE_TYPE_CHOICES, STUDENT_STATUS_CHOICES, INSTALLMENT_STATUS_CHOICES, GENDER_CHOICES
)
from common.utils import generate_certificate_number

class Course(models.Model):
    course_name = models.CharField(max_length=100)
    default_duration = models.CharField(max_length=50, default="6 months")
    skills_list = models.JSONField(default=list, help_text="List of skills for this course")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.course_name


class Student(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True) # Unique per training program
    phone = models.CharField(max_length=15, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    
    institute = models.CharField(max_length=200)
    course_at_institute = models.CharField(max_length=100)
    student_type = models.CharField(max_length=30, choices=STUDENT_TYPE_CHOICES)
    program_name = models.CharField(max_length=100)
    
    department = models.ForeignKey(
        'employee_onboarding.Department',
        on_delete=models.PROTECT,
        related_name='students'
    )
    mentor = models.CharField(max_length=100, blank=True, null=True)
    joining_date = models.DateField()
    completion_date = models.DateField()
    
    project_description = models.TextField(blank=True, null=True)
    cert_type = models.CharField(max_length=30, choices=CERTIFICATE_TYPE_CHOICES)
    cert_no = models.CharField(max_length=30, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=STUDENT_STATUS_CHOICES, default='ACTIVE')
    cert_pdf = models.FileField(upload_to='certificates/', blank=True, null=True)
    
    total_fees = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # New Fields
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default='MALE')
    father_name = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    enrolled_course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_students'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def training_duration(self):
        """
        Calculates training duration in days or weeks.
        """
        delta = self.completion_date - self.joining_date
        days = delta.days
        if days < 7:
            return f"{days} days"
        weeks = days // 7
        remaining_days = days % 7
        if remaining_days == 0:
            return f"{weeks} weeks"
        return f"{weeks} weeks, {remaining_days} days"

    def save(self, *args, **kwargs):
        if not self.cert_no:
            self.cert_no = generate_certificate_number()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.cert_no})"


class StudentFeeInstallment(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='installments'
    )
    installment_number = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=INSTALLMENT_STATUS_CHOICES,
        default='UNPAID'
    )
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Installment {self.installment_number} for {self.student.name} ({self.status})"


class StudentCertificate(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE
    )
    skill_ratings = models.JSONField(default=dict, help_text="Dictionary of skill -> rating")
    show_dates = models.BooleanField(default=True)
    issue_date = models.DateField()
    serial_no = models.CharField(max_length=50, unique=True)
    pdf_file = models.FileField(upload_to='certificates/', blank=True, null=True)
    cert_content = models.TextField(blank=True, null=True, help_text="Customized content text")
    place = models.CharField(max_length=100, default="Mohali")
    
    # Validation & Approval Workflow Fields
    early_generation_reason = models.TextField(blank=True, null=True)
    calculated_completed_duration = models.CharField(max_length=100, blank=True, null=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_certificates'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.serial_no} - {self.student.name}"


def student_upload_to_uuid_filename(instance, filename):
    import uuid
    import os
    ext = os.path.splitext(filename)[1].lower()
    uuid_filename = f"{uuid.uuid4()}{ext}"
    return f"students/{instance.student.id}/docs/{uuid_filename}"


class StudentDocument(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=50)  # RESUME, AADHAAR, COLLEGE_ID, JOINING_LETTER, FEE_RECEIPT, OTHER
    label = models.CharField(max_length=200, blank=True, null=True)
    file = models.FileField(upload_to=student_upload_to_uuid_filename)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_student_documents'
    )
    upload_date = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.original_filename and self.file:
            import os
            self.original_filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Student {self.student.name} - {self.doc_type}"


