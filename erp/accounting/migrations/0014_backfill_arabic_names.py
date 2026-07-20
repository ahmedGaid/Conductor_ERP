"""Backfill Arabic names onto charts of accounts seeded before `name_ar` existed.

The map is a frozen snapshot of `services.seeding.COA` (and the baseline tax codes / cost centers)
as of this migration — migrations must not import the live seeding module, whose contents change.
Only blank `name_ar` values are filled, and only on rows whose English name is still the seeded one,
so a company that renamed an account keeps its own wording.
"""
from django.db import migrations

ACCOUNTS = {
    "1": ("Assets", "الأصول"),
    "1000": ("Cash", "النقدية"),
    "1010": ("Bank", "البنك"),
    "1100": ("Accounts Receivable", "الذمم المدينة"),
    "1190": ("VAT Input (Recoverable)", "ضريبة القيمة المضافة — مدخلات"),
    "1200": ("Inventory", "المخزون"),
    "1500": ("Fixed Assets", "الأصول الثابتة"),
    "1590": ("Accumulated Depreciation", "مجمع الإهلاك"),
    "2": ("Liabilities", "الالتزامات"),
    "2000": ("Accounts Payable", "الذمم الدائنة"),
    "2100": ("VAT Payable", "ضريبة القيمة المضافة المستحقة"),
    "2150": ("Goods Received Not Invoiced", "بضاعة واردة بدون فاتورة"),
    "3": ("Equity", "حقوق الملكية"),
    "3000": ("Share Capital", "رأس المال"),
    "3100": ("Retained Earnings", "الأرباح المحتجزة"),
    "3110": ("Inventory Opening Balance", "رصيد المخزون الافتتاحي"),
    "4": ("Income", "الإيرادات"),
    "4000": ("Sales Revenue", "إيرادات المبيعات"),
    "4090": ("Sales Returns", "مردودات المبيعات"),
    "4200": ("Gain on Asset Disposal", "أرباح بيع الأصول"),
    "5": ("Expenses", "المصروفات"),
    "5000": ("Cost of Goods Sold", "تكلفة البضاعة المباعة"),
    "5100": ("Rent Expense", "مصروف الإيجار"),
    "5200": ("Salaries Expense", "مصروف الرواتب"),
    "5300": ("Depreciation Expense", "مصروف الإهلاك"),
    "5400": ("Loss on Asset Disposal", "خسائر بيع الأصول"),
    "5900": ("Inventory Adjustment", "تسوية المخزون"),
    "6100": ("Bank Charges", "مصاريف بنكية"),
}

COST_CENTERS = {
    "CC-SALES": ("Sales Dept", "إدارة المبيعات"),
    "CC-OPS": ("Operations", "العمليات"),
    "CC-ADMIN": ("Administration", "الإدارة"),
}

TAX_CODES = {
    "VAT14": ("VAT 14%", "ضريبة القيمة المضافة 14%"),
    "VAT0": ("Exempt / 0%", "معفاة / 0%"),
}


def _fill(model, mapping):
    for code, (seeded_en, name_ar) in mapping.items():
        model.objects.filter(code=code, name=seeded_en, name_ar="").update(name_ar=name_ar)


def forwards(apps, schema_editor):
    _fill(apps.get_model("accounting", "Account"), ACCOUNTS)
    _fill(apps.get_model("accounting", "CostCenter"), COST_CENTERS)
    _fill(apps.get_model("accounting", "TaxCode"), TAX_CODES)


def backwards(apps, schema_editor):
    """Clear only the Arabic names this migration set — the column itself is dropped by 0013."""
    for model_name, mapping in (
        ("Account", ACCOUNTS), ("CostCenter", COST_CENTERS), ("TaxCode", TAX_CODES)
    ):
        model = apps.get_model("accounting", model_name)
        for code, (seeded_en, name_ar) in mapping.items():
            model.objects.filter(code=code, name=seeded_en, name_ar=name_ar).update(name_ar="")


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0013_account_name_ar_costcenter_name_ar_taxcode_name_ar"),
    ]

    operations = [migrations.RunPython(forwards, backwards)]
