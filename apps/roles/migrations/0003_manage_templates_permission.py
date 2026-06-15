from django.db import migrations

def create_manage_templates_permission(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Role = apps.get_model('roles', 'Role')
    
    perm, created = Permission.objects.get_or_create(
        codename='onboarding.manage_templates',
        defaults={
            'name': 'Manage Letter Templates',
            'module': 'onboarding'
        }
    )
    
    # Assign this permission to ADMIN and HR roles by default
    for role in Role.objects.filter(code__in=['ADMIN', 'HR']):
        role.permissions.add(perm)

def remove_manage_templates_permission(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.filter(codename='onboarding.manage_templates').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('roles', '0002_dashboard_permission'),
    ]

    operations = [
        migrations.RunPython(create_manage_templates_permission, remove_manage_templates_permission),
    ]
