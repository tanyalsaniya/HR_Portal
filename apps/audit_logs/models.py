from django.db import models
from django.conf import settings

class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50) # CREATE, UPDATE, DELETE, etc.
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        actor_name = self.actor.username if self.actor else "System"
        return f"{actor_name} - {self.action} on {self.model_name} at {self.timestamp}"
