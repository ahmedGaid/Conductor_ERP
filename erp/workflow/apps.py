from django.apps import AppConfig


class WorkflowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erp.workflow"
    label = "workflow"
    verbose_name = "Workflow engine"

    def ready(self) -> None:
        from erp.core.events import bus
        from erp.notifications.webhook_catalog import WEBHOOK_EVENT_CATALOG

        from . import triggers

        for _name in WEBHOOK_EVENT_CATALOG:
            bus.subscribe(_name, triggers.on_domain_event)
