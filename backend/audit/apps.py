from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = 'audit'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Import signals so Django registers the handlers at startup.
        # This must happen inside ready() to avoid AppRegistryNotReady errors.
        import audit.signals  # noqa: F401
