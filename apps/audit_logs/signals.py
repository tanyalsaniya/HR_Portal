# apps/audit_logs/signals.py
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from common.middleware import get_current_user
from .models import AuditLog

# Import models dynamically to avoid import-time dependency loops
from salary.models import SalaryStructure, SalarySlip
from exit_formality.models import ExitRequest
from student_certificate.models import Student, StudentFeeInstallment

def log_action(actor, action, instance, description):
    try:
        model_name = instance.__class__.__name__
        object_id = str(instance.id) if hasattr(instance, 'id') else None
        AuditLog.objects.create(
            actor=actor,
            action=action,
            model_name=model_name,
            object_id=object_id,
            description=description
        )
    except Exception as e:
        print(f"Error creating audit log: {e}")


@receiver(post_save, sender=SalaryStructure)
def salary_structure_post_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    action = "CREATE" if created else "UPDATE"
    emp = instance.employee
    emp_identifier = emp.emp_id if emp else instance.bitrix_user_id
    desc = f"Salary structure for employee {emp_identifier} was {'created' if created else 'updated'}."
    log_action(actor, action, instance, desc)


@receiver(post_save, sender=SalarySlip)
def salary_slip_post_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    action = "CREATE" if created else "UPDATE"
    emp = instance.employee
    emp_identifier = emp.emp_id if emp else instance.bitrix_user_id
    desc = f"Salary slip {instance.payslip_no} for employee {emp_identifier} for {instance.month}/{instance.year} was {'generated' if created else 'updated'}."
    log_action(actor, action, instance, desc)


@receiver(post_save, sender=ExitRequest)
def exit_request_post_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    action = "CREATE" if created else "UPDATE"
    emp = instance.employee
    emp_identifier = emp.emp_id if emp else instance.bitrix_user_id
    desc = f"Exit request for employee {emp_identifier} was {'initiated' if created else 'updated to ' + instance.status}."
    log_action(actor, action, instance, desc)


@receiver(post_save, sender=Student)
def student_post_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    action = "CREATE" if created else "UPDATE"
    desc = f"Student {instance.name} ({instance.cert_no}) was {'registered' if created else 'updated to ' + instance.status}."
    log_action(actor, action, instance, desc)


@receiver(post_save, sender=StudentFeeInstallment)
def student_installment_post_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    action = "CREATE" if created else "UPDATE"
    desc = f"Installment {instance.installment_number} for student {instance.student.name} was {'defined' if created else 'updated to ' + instance.status}."
    log_action(actor, action, instance, desc)
