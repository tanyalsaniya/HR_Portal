# apps/audit_logs/signals.py
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from common.middleware import get_current_user
from .models import AuditLog

# Import models dynamically to avoid import-time dependency loops
from employee_onboarding.models import Employee
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


@receiver(pre_save, sender=Employee)
def employee_pre_save(sender, instance, **kwargs):
    if instance.id:
        try:
            instance._old_instance = Employee.objects.get(pk=instance.pk)
        except Employee.DoesNotExist:
            instance._old_instance = None
    else:
        instance._old_instance = None


@receiver(post_save, sender=Employee)
def employee_post_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    
    if created:
        desc = f"Employee {instance.first_name} {instance.last_name} ({instance.emp_id}) was onboarded."
        log_action(actor, "CREATE", instance, desc)
    else:
        old_inst = getattr(instance, '_old_instance', None)
        if instance.is_deleted and old_inst and not old_inst.is_deleted:
            desc = f"Employee {instance.first_name} {instance.last_name} ({instance.emp_id}) was soft-deleted."
            log_action(actor, "DELETE", instance, desc)
            return

        if old_inst:
            changes = []
            fields_to_compare = [
                'first_name', 'last_name', 'email', 'phone', 'alternate_phone',
                'dob', 'gender', 'address_line1', 'address_line2', 'city', 'state', 'pin_code',
                'department', 'designation', 'employment_type', 'joining_date',
                'notice_period_days', 'bond_period_months', 'emergency_contact_name',
                'emergency_relationship', 'emergency_phone', 'aadhaar_encrypted', 'pan_encrypted',
                'profile_photo', 'status', 'onboarding_complete'
            ]
            
            for field in fields_to_compare:
                old_val = getattr(old_inst, field)
                new_val = getattr(instance, field)
                
                if old_val != new_val:
                    if field in ['aadhaar_encrypted', 'pan_encrypted']:
                        changes.append(f"Sensitive field '{field.replace('_encrypted', '')}' was updated")
                    else:
                        changes.append(f"'{field}' changed from '{old_val}' to '{new_val}'")
            
            if changes:
                desc = f"Employee {instance.first_name} {instance.last_name} ({instance.emp_id}) updated: " + ", ".join(changes)
                log_action(actor, "UPDATE", instance, desc)


@receiver(post_save, sender=SalaryStructure)
def salary_structure_post_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    action = "CREATE" if created else "UPDATE"
    desc = f"Salary structure for employee {instance.employee.emp_id} was {'created' if created else 'updated'}."
    log_action(actor, action, instance, desc)


@receiver(post_save, sender=SalarySlip)
def salary_slip_post_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    action = "CREATE" if created else "UPDATE"
    desc = f"Salary slip {instance.payslip_no} for employee {instance.employee.emp_id} for {instance.month}/{instance.year} was {'generated' if created else 'updated'}."
    log_action(actor, action, instance, desc)


@receiver(post_save, sender=ExitRequest)
def exit_request_post_save(sender, instance, created, **kwargs):
    actor = get_current_user()
    action = "CREATE" if created else "UPDATE"
    desc = f"Exit request for employee {instance.employee.emp_id} was {'initiated' if created else 'updated to ' + instance.status}."
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
