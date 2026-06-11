from django.db import models

class Permission(models.Model):
    name = models.CharField(max_length=150)
    codename = models.CharField(max_length=100, unique=True)
    module = models.CharField(max_length=100) # e.g. "onboarding", "salary", "exit", "student", "audit", "roles"

    def __str__(self):
        return f"{self.module} - {self.name} ({self.codename})"

class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=100, unique=True) # e.g. "ADMIN", "HR", "RECRUITER"
    permissions = models.ManyToManyField(Permission, blank=True, related_name='roles')
    is_active = models.BooleanField(default=True)
    is_system = models.BooleanField(default=False) # ADMIN and HR roles cannot be deleted or renamed

    def __str__(self):
        return f"{self.name} ({self.code})"
