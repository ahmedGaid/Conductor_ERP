from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erp.accounting"
    label = "accounting"
    verbose_name = "Accounting & Finance"
