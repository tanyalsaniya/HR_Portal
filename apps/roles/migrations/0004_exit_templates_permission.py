from django.db import migrations

def create_exit_templates_permission(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Role = apps.get_model('roles', 'Role')
    
    perm, created = Permission.objects.get_or_create(
        codename='exit.manage_templates',
        defaults={
            'name': 'Manage Exit Letter Templates',
            'module': 'exit'
        }
    )
    
    # Assign this permission ONLY to ADMIN role by default
    for role in Role.objects.filter(code='ADMIN'):
        role.permissions.add(perm)

def remove_exit_templates_permission(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.filter(codename='exit.manage_templates').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('roles', '0003_manage_templates_permission'),
    ]

    operations = [
        migrations.RunPython(create_exit_templates_permission, remove_exit_templates_permission),
    ]
