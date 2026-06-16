from django.apps import AppConfig

class ExitFormalityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'exit_formality'

    def ready(self):
        import exit_formality.signals
