from django.apps import AppConfig


class ImportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erp.imports"
    label = "imports"
    verbose_name = "Smart Import Engine"

    def ready(self) -> None:
        from . import adapters  # noqa: F401  (import registers every adapter)
