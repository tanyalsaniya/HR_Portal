from django.db import models
from django.conf import settings
from decimal import Decimal
from rules import (
    STUDENT_TYPE_CHOICES, CERTIFICATE_TYPE_CHOICES, STUDENT_STATUS_CHOICES, INSTALLMENT_STATUS_CHOICES
)
from common.utils import generate_certificate_number

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
