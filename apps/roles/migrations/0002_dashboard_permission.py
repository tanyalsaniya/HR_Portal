from django.db import migrations

def create_dashboard_permission(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Role = apps.get_model('roles', 'Role')
    
    perm, created = Permission.objects.get_or_create(
        codename='dashboard.read',
        defaults={
            'name': 'View Dashboard',
            'module': 'dashboard'
        }
    )
    
    for role in Role.objects.filter(is_active=True):
        role.permissions.add(perm)

def remove_dashboard_permission(apps, schema_editor):
    Permission = apps.get_model('roles', 'Permission')
    Permission.objects.filter(codename='dashboard.read').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('roles', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_dashboard_permission, remove_dashboard_permission),
    ]
