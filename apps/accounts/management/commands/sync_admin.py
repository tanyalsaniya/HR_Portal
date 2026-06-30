"""
management/commands/sync_admin.py

Reads ADMIN_EMAIL and ADMIN_PASSWORD from the .env file and
creates or updates the superadmin account automatically.

Usage:
  python manage.py sync_admin

This is also called automatically on every server startup via
the AppConfig.ready() hook in accounts/apps.py.
"""
import os
import logging
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Sync the admin user credentials from the .env file "
        "(ADMIN_EMAIL + ADMIN_PASSWORD). "
        "Change those values and run this command (or restart the server) "
        "to apply new credentials."
    )

    def handle(self, *args, **options):
        User = get_user_model()
        verbosity = options.get('verbosity', 1)

        new_email = os.getenv('ADMIN_EMAIL', '').strip()
        new_password = os.getenv('ADMIN_PASSWORD', '').strip()

        if not new_email or not new_password:
            if verbosity > 0:
                self.stdout.write(self.style.WARNING(
                    "WARNING: ADMIN_EMAIL or ADMIN_PASSWORD not found in environment / .env file.\n"
                    "         Add them to your .env and restart the server."
                ))
            return

        # Find existing admin: first by new email, then any superuser
        admin = (
            User.objects.filter(email=new_email).first()
            or User.objects.filter(is_superuser=True).first()
        )

        if admin:
            changed = False
            if admin.email != new_email:
                admin.email = new_email
                changed = True
            if admin.username != new_email:
                admin.username = new_email
                changed = True
            if not admin.check_password(new_password):
                admin.set_password(new_password)
                changed = True

            if changed:
                admin.save()
                if verbosity > 0:
                    self.stdout.write(self.style.SUCCESS(
                        f"[OK] Admin credentials updated -> {new_email}"
                    ))
                logger.info(f"Admin credentials synced from .env -> {new_email}")
            else:
                if verbosity > 0:
                    self.stdout.write(
                        f"[INFO] Admin credentials already match .env ({new_email}). Nothing changed."
                    )
        else:
            # No superuser at all — create fresh
            try:
                from roles.models import Role
                admin_role = Role.objects.filter(code='ADMIN').first()
            except Exception:
                admin_role = None

            admin = User.objects.create_superuser(
                email=new_email,
                username=new_email,
                password=new_password,
            )
            if admin_role:
                admin.role = admin_role
                admin.save()

            if verbosity > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"[OK] Superadmin created -> {new_email}"
                ))
            logger.info(f"Superadmin created from .env -> {new_email}")


