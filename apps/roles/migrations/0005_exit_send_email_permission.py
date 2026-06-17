from django.db import migrations

def create_exit_send_email_permission(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Role = apps.get_model('roles', 'Role')
    
    perm, created = Permission.objects.get_or_create(
        codename='exit.send_email',
        defaults={
            'name': 'Send Exit Documents Email',
            'module': 'exit'
        }
    )
    
    # Assign this permission ONLY to ADMIN role by default
    for role in Role.objects.filter(code='ADMIN'):
        role.permissions.add(perm)

def remove_exit_send_email_permission(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.filter(codename='exit.send_email').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('roles', '0004_exit_templates_permission'),
    ]

    operations = [
        migrations.RunPython(create_exit_send_email_permission, remove_exit_send_email_permission),
    ]
