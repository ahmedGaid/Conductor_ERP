from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erp.core"
    label = "core"
    verbose_name = "Core platform"
