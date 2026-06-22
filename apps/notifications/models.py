from django.db import models
from django.conf import settings

class Notification(models.Model):
    NOTIF_TYPE_CHOICES = (
        ('INFO', 'Info'),
        ('SUCCESS', 'Success'),
        ('WARNING', 'Warning'),
        ('URGENT', 'Urgent'),
        ('ERROR', 'Error'),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPE_CHOICES, default='INFO')
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username} - Read: {self.is_read}"


class BitrixSyncLog(models.Model):
    STATUS_CHOICES = (
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('PERMANENTLY_FAILED', 'Permanently Failed'),
    )
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    employee_name = models.CharField(max_length=200, blank=True, null=True)
    action_type = models.CharField(max_length=100) # e.g. 'Contact Create', 'Contact Update', 'Exit Update'
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='FAILED')
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Sync Log for {self.employee_name} ({self.action_type}) - Status: {self.status}"

