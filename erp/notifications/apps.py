from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erp.notifications"
    label = "notifications"
    verbose_name = "Notifications & Integration Adapters"

    def ready(self) -> None:
        # Subscribe the notification handlers to the domain events (invoice / ticket escalation).
        # Imported here so binding happens once the app registry is ready. Subscriber failures are
        # isolated by the bus — they can never break the publisher (invoicing / escalation).
        from . import handlers  # noqa: F401

        handlers.register()
