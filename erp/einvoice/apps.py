from django.apps import AppConfig


class EInvoiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erp.einvoice"
    label = "einvoice"
    verbose_name = "E-Invoicing (ETA)"

    def ready(self) -> None:
        # Register the event-bus subscriber that records an ETA e-invoice when a sales order
        # is invoiced. Imported here so it binds once the app registry is ready.
        from . import handlers  # noqa: F401

        handlers.register()
