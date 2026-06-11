import uuid
import datetime
from django.db import models
from django.conf import settings
from rules import (
    EXIT_TYPE_CHOICES, EXIT_STATUS_CHOICES, KT_STATUS_CHOICES, EXIT_LINK_EXPIRY_DAYS
)

class ExitRequest(models.Model):
    employee = models.ForeignKey(
        'employee_onboarding.Employee',
        on_delete=models.CASCADE,
        related_name='exit_requests'
    )
    resignation_date = models.DateField()
    last_working_day = models.DateField()
    exit_type = models.CharField(max_length=20, choices=EXIT_TYPE_CHOICES)
    exit_reason = models.TextField()  # min 20 chars validation in serializer
    notice_waiver = models.BooleanField(default=False)
    notice_letter_required = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=EXIT_STATUS_CHOICES, default='PENDING')
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='initiated_exits'
    )
    initiated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Exit for {self.employee.emp_id} ({self.status})"

class ExitSecureLink(models.Model):
    exit_request = models.ForeignKey(ExitRequest, on_delete=models.CASCADE, related_name='secure_links')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = datetime.datetime.now() + datetime.timedelta(days=EXIT_LINK_EXPIRY_DAYS)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        # Handle timezone aware vs naive
        from django.utils import timezone
        now = timezone.now() if timezone.is_aware(self.expires_at) else datetime.datetime.now()
        return now > self.expires_at or self.used

    def __str__(self):
        return f"Link for {self.exit_request.employee.emp_id} (Expired: {self.is_expired})"

class ExitFormResponse(models.Model):
    exit_request = models.OneToOneField(ExitRequest, on_delete=models.CASCADE, related_name='form_response')
    
    # Asset Return Checkboxes + text
    asset_laptop_returned = models.BooleanField(default=False)
    asset_laptop_remarks = models.TextField(blank=True, null=True)
    
    asset_id_returned = models.BooleanField(default=False)
    asset_id_remarks = models.TextField(blank=True, null=True)
    
    asset_access_card_returned = models.BooleanField(default=False)
    asset_access_card_remarks = models.TextField(blank=True, null=True)
    
    asset_others_details = models.TextField(blank=True, null=True)

    # Knowledge Transfer details
    kt_status = models.CharField(max_length=20, choices=KT_STATUS_CHOICES)
    kt_handover_to = models.CharField(max_length=100, blank=True, null=True)
    kt_remarks = models.TextField(blank=True, null=True)

    # Feedback questionnaire
    reason_dropdown = models.CharField(max_length=100)
    reason_details = models.TextField(blank=True, null=True)
    
    rating_env = models.PositiveIntegerField() # 1 to 5
    rating_mgmt = models.PositiveIntegerField() # 1 to 5
    recommend = models.CharField(max_length=10) # Yes / No / Maybe
    
    personal_email = models.EmailField()
    personal_phone = models.CharField(max_length=15, blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response for {self.exit_request.employee.emp_id}"
