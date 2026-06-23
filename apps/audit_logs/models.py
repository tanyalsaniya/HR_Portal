from django.db import models
from django.conf import settings
from common.middleware import get_current_user

class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    # Persist values when actor is deleted
    user_id_val = models.IntegerField(null=True, blank=True)
    user_name = models.CharField(max_length=150, blank=True, null=True)
    user_role = models.CharField(max_length=50, blank=True, null=True)
    
    action = models.CharField(max_length=100) # USER_LOGIN, STUDENT_CREATED, etc.
    module_name = models.CharField(max_length=100, blank=True, null=True) # e.g. student, employee, auth, salary
    description = models.TextField()
    
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, default='SUCCESS') # SUCCESS or FAILED
    timestamp = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionError("Audit logs are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Allow deletion only if the actor performing the delete is a superuser
        user = get_current_user()
        if user and user.is_superuser:
            super().delete(*args, **kwargs)
        else:
            raise PermissionError("Only Super Admin can permanently delete audit logs.")

    def __str__(self):
        actor_name = self.user_name or (self.actor.username if self.actor else "System")
        return f"{actor_name} - {self.action} on {self.module_name} at {self.timestamp}"

