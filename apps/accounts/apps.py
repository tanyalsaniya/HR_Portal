"""
accounts/apps.py

Auto-syncs admin credentials from .env on every server startup.
"""
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        """Called once when Django finishes loading all apps."""
        import os

        # Only run when the actual server process starts (not during migrations, tests, etc.)
        run_main = os.environ.get('RUN_MAIN') or os.environ.get('WERKZEUG_RUN_MAIN')
        is_server = os.environ.get('SERVER_SOFTWARE', '') or run_main

        # Always attempt the sync (safe — it only writes if credentials differ)
        try:
            from django.core.management import call_command
            call_command('sync_admin', verbosity=0)
        except Exception:
            # Silently ignore during migrations / initial setup when tables don't exist yet
            pass
