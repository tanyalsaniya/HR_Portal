# scripts/create_super_admin.py
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model


def sync_admin_credentials():
    """
    Reads ADMIN_EMAIL and ADMIN_PASSWORD from the environment (.env file)
    and creates or updates the superadmin user accordingly.
    Change values in .env and restart the server to apply new credentials.
    """
    User = get_user_model()

    new_email = os.getenv('ADMIN_EMAIL', 'admin@devexhub.com').strip()
    new_password = os.getenv('ADMIN_PASSWORD', 'Admin@123').strip()

    if not new_email or not new_password:
        print("⚠️  ADMIN_EMAIL or ADMIN_PASSWORD not set in .env. Skipping admin sync.")
        return

    # Look for existing superuser by email OR by old default emails
    admin = (
        User.objects.filter(email=new_email).first()
        or User.objects.filter(is_superuser=True).first()
    )

    if admin:
        changed = False
        if admin.email != new_email or admin.username != new_email:
            admin.email = new_email
            admin.username = new_email
            changed = True
        if not admin.check_password(new_password):
            admin.set_password(new_password)
            changed = True
        if changed:
            admin.save()
            print(f"✅  Admin credentials updated → {new_email}")
        else:
            print(f"ℹ️   Admin credentials unchanged ({new_email}).")
    else:
        # No superuser exists yet — create one
        from roles.models import Role
        admin_role = Role.objects.filter(code='ADMIN').first()
        admin = User.objects.create_superuser(
            email=new_email,
            username=new_email,
            password=new_password,
        )
        if admin_role:
            admin.role = admin_role
            admin.save()
        print(f"✅  Superuser created → {new_email}")


if __name__ == '__main__':
    sync_admin_credentials()
