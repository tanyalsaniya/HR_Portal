# apps/audit_logs/signals.py
import logging
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.apps import apps
from django.core.serializers.json import DjangoJSONEncoder
import json

from common.middleware import get_current_user, get_current_request
from .models import AuditLog

logger = logging.getLogger(__name__)

def get_client_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_user_agent(request):
    if not request:
        return None
    return request.META.get('HTTP_USER_AGENT')

def log_action(actor=None, action=None, module_name=None, description=None, old_values=None, new_values=None, status='SUCCESS', request=None):
    try:
        if not actor:
            actor = get_current_user()
        if not request:
            request = get_current_request()
            
        ip = get_client_ip(request)
        ua = get_user_agent(request)
        
        user_id_val = None
        user_name = "System"
        user_role = None
        
        if actor and actor.is_authenticated:
            user_id_val = actor.id
            user_name = actor.username
            user_role = actor.role.code if getattr(actor, 'role', None) else None
        elif request and hasattr(request, 'user') and request.user and request.user.is_authenticated:
            actor = request.user
            user_id_val = actor.id
            user_name = actor.username
            user_role = actor.role.code if getattr(actor, 'role', None) else None
            
        AuditLog.objects.create(
            actor=actor if (actor and actor.is_authenticated) else None,
            user_id_val=user_id_val,
            user_name=user_name,
            user_role=user_role,
            action=action,
            module_name=module_name,
            description=description,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip,
            user_agent=ua,
            status=status
        )
    except Exception as e:
        logger.error(f"Error creating audit log: {e}")


# --- AUTH SIGNALS ---

@receiver(user_logged_in)
def log_user_logged_in(sender, request, user, **kwargs):
    log_action(
        actor=user,
        action="USER_LOGIN",
        module_name="auth",
        description=f"User {user.username} logged in successfully.",
        request=request
    )

@receiver(user_logged_out)
def log_user_logged_out(sender, request, user, **kwargs):
    if user:
        log_action(
            actor=user,
            action="USER_LOGOUT",
            module_name="auth",
            description=f"User {user.username} logged out.",
            request=request
        )

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get('username', 'unknown')
    log_action(
        actor=None,
        action="FAILED_LOGIN_ATTEMPT",
        module_name="auth",
        description=f"Failed login attempt for username: {username}.",
        status="FAILED",
        request=request
    )


# --- CRUD TRACKING HELPER ACTIONS ---

def serialize_model_instance(instance):
    data = {}
    for field in instance._meta.fields:
        val = getattr(instance, field.name)
        if val is None:
            data[field.name] = None
        elif isinstance(val, (int, float, bool, str, dict, list)):
            data[field.name] = val
        else:
            # Handle date/datetime/decimal/UUID/ForeignKey values
            data[field.name] = str(val)
    return data

def track_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            original = sender.objects.get(pk=instance.pk)
            old_data = serialize_model_instance(original)
            new_data = serialize_model_instance(instance)
            
            changed_fields_old = {}
            changed_fields_new = {}
            for field, old_val in old_data.items():
                new_val = new_data.get(field)
                if old_val != new_val:
                    if field == 'password':
                        changed_fields_old[field] = '********'
                        changed_fields_new[field] = '********'
                    else:
                        changed_fields_old[field] = old_val
                        changed_fields_new[field] = new_val
            
            instance._changed_fields_old = changed_fields_old
            instance._changed_fields_new = changed_fields_new
        except sender.DoesNotExist:
            pass

def track_post_save(sender, instance, created, **kwargs):
    model_name = sender.__name__
    module_name = sender._meta.app_label
    
    if created:
        action = f"{model_name.upper()}_CREATED"
        new_values = serialize_model_instance(instance)
        if 'password' in new_values:
            new_values['password'] = '********'
        old_values = None
        description = f"Created a new {model_name} (ID: {instance.pk})."
    else:
        action = f"{model_name.upper()}_UPDATED"
        old_values = getattr(instance, '_changed_fields_old', {})
        new_values = getattr(instance, '_changed_fields_new', {})
        if not old_values and not new_values:
            return
        description = f"Updated {model_name} fields: {', '.join(old_values.keys())} (ID: {instance.pk})."
        
    log_action(
        action=action,
        module_name=module_name,
        description=description,
        old_values=old_values,
        new_values=new_values
    )

def track_post_delete(sender, instance, **kwargs):
    model_name = sender.__name__
    module_name = sender._meta.app_label
    action = f"{model_name.upper()}_DELETED"
    
    old_values = serialize_model_instance(instance)
    if 'password' in old_values:
        old_values['password'] = '********'
        
    description = f"Deleted {model_name} (ID: {instance.pk})."
    
    log_action(
        action=action,
        module_name=module_name,
        description=description,
        old_values=old_values,
        new_values=None
    )


# --- DYNAMIC SIGNAL REGISTRATION ---

def register_signals():
    models_to_track = [
        # Accounts
        ('accounts', 'User'),
        # Roles
        ('roles', 'Role'),
        # Student Certificate
        ('student_certificate', 'Course'),
        ('student_certificate', 'Student'),
        ('student_certificate', 'StudentFeeInstallment'),
        ('student_certificate', 'StudentCertificate'),
        # Salary
        ('salary', 'SalaryStructure'),
        ('salary', 'SalarySlip'),
        ('salary', 'SalaryIncrementReminder'),
        ('salary', 'SalaryIncrementApproval'),
        ('salary', 'EmployeeBankDetail'),
        # Exit Formality
        ('exit_formality', 'ExitRequest'),
        ('exit_formality', 'ExitFormResponse'),
        ('exit_formality', 'ExitFFSettlement'),
        # Employee Onboarding
        ('employee_onboarding', 'Department'),
        ('employee_onboarding', 'EmployeeDocument'),
        ('employee_onboarding', 'LetterTemplate'),
    ]
    
    for app_label, model_name in models_to_track:
        try:
            model = apps.get_model(app_label, model_name)
            pre_save.connect(track_pre_save, sender=model, dispatch_uid=f"audit_pre_{app_label}_{model_name}")
            post_save.connect(track_post_save, sender=model, dispatch_uid=f"audit_post_{app_label}_{model_name}")
            post_delete.connect(track_post_delete, sender=model, dispatch_uid=f"audit_delete_{app_label}_{model_name}")
        except LookupError:
            logger.warning(f"Could not find model {app_label}.{model_name} for audit logs")

# Register the CRUD signals dynamically
register_signals()
