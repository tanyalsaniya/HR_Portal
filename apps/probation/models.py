from django.db import models
from employee_onboarding.models import SyncedEmployee

class ProbationChecklist(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    # Store questions as a list of dictionaries: [{"id": "q1", "label": "Productivity goals achieved?", "type": "textarea"}, ...]
    questions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class ChecklistAssignment(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Submitted', 'Submitted'),
        ('Analyzed', 'Analyzed'),
    )
    checklist = models.ForeignKey(ProbationChecklist, on_delete=models.CASCADE, related_name='assignments')
    employee = models.ForeignKey(SyncedEmployee, on_delete=models.CASCADE, related_name='probation_assignments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    assigned_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.checklist.title} assigned to {self.employee.first_name} {self.employee.last_name or ''}"


class ChecklistResponse(models.Model):
    assignment = models.OneToOneField(ChecklistAssignment, on_delete=models.CASCADE, related_name='response')
    # Store answers as mapping: {"q1": "Yes, I completed my tasks...", "q2": "..."}
    answers = models.JSONField(default=dict)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response for {self.assignment}"


class AIReport(models.Model):
    assignment = models.OneToOneField(ChecklistAssignment, on_delete=models.CASCADE, related_name='ai_report')
    employee = models.ForeignKey(SyncedEmployee, on_delete=models.CASCADE, related_name='ai_reports')
    scores = models.JSONField(default=dict) # {"overall_score": 89, "productivity_score": 91, ...}
    trend = models.CharField(max_length=50) # e.g. "Improving", "Steady", "Declining"
    strengths = models.JSONField(default=list) # ["Completes assigned work", ...]
    improvements = models.JSONField(default=list) # ["Time estimation", ...]
    recommendation = models.CharField(max_length=100) # e.g. "Continue", "Extend", "Confirm"
    summary = models.TextField()
    insights = models.JSONField(default=dict) # {"positive": [...], "negative": [...]}
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AI Report for {self.employee.first_name} - {self.created_at.strftime('%Y-%m-%d')}"


class FinalProbationReport(models.Model):
    employee = models.OneToOneField(SyncedEmployee, on_delete=models.CASCADE, related_name='final_probation_report')
    average_score = models.FloatField()
    best_week = models.CharField(max_length=50)
    lowest_week = models.CharField(max_length=50)
    overall_trend = models.CharField(max_length=50)
    strengths = models.JSONField(default=list)
    improvements = models.JSONField(default=list)
    challenges = models.JSONField(default=list)
    final_recommendation = models.CharField(max_length=100)
    confidence = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Final Probation Report for {self.employee.first_name} {self.employee.last_name or ''}"
