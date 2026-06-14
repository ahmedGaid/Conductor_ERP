from django.apps import AppConfig


class WorkflowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erp.workflow"
    label = "workflow"
    verbose_name = "Workflow engine"
