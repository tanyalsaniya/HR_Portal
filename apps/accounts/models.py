from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    role = models.ForeignKey(
        'roles.Role',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        role_name = self.role.name if self.role else "No Role"
        return f"{self.username} ({role_name})"
