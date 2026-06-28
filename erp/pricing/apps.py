from django.apps import AppConfig


class PricingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erp.pricing"
    label = "pricing"
    verbose_name = "Pricing & Price Lists"
