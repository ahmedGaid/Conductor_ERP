"""Build :class:`erp.core.exports.ReportTable` views of the accounting reports.

Column/section labels are bilingual (en/ar) chosen by ``lang`` so a download carries proper headers
without reaching into the frontend i18n bundle. Money cells stay integer minor units — the core
renderer converts to major units.
"""
from __future__ import annotations

from erp.core.exports import Column, ReportTable


def _l(en: str, ar: str, lang: str) -> str:
    return ar if lang == "ar" else en


def _money(label_en: str, label_ar: str, key: str, lang: str) -> Column:
    return Column(key, _l(label_en, label_ar, lang), kind="money", align="end")


def trial_balance_table(tb, lang: str, period: str | None = None) -> ReportTable:
    cols = [
        Column("code", _l("Code", "الرمز", lang)),
        Column("name", _l("Account", "الحساب", lang)),
        _money("Debit", "مدين", "debit", lang),
        _money("Credit", "دائن", "credit", lang),
        _money("Balance", "الرصيد", "balance", lang),
    ]
    rows = [
        {"code": r.account_code, "name": r.account_name,
         "debit": r.debit, "credit": r.credit, "balance": r.balance}
        for r in tb.rows
    ]
    footer = [{"code": "", "name": _l("Total", "الإجمالي", lang),
               "debit": tb.total_debit, "credit": tb.total_credit, "balance": ""}]
    meta = [(_l("Period", "الفترة", lang), period)] if period else []
    return ReportTable(title=_l("Trial Balance", "ميزان المراجعة", lang),
                       columns=cols, rows=rows, footer=footer, meta=meta, rtl=(lang == "ar"))


def general_ledger_table(gl, lang: str, period: str | None = None) -> ReportTable:
    cols = [
        Column("date", _l("Date", "التاريخ", lang)),
        Column("entry", _l("Entry", "القيد", lang)),
        Column("memo", _l("Memo", "البيان", lang)),
        _money("Debit", "مدين", "debit", lang),
        _money("Credit", "دائن", "credit", lang),
        _money("Balance", "الرصيد", "balance", lang),
    ]
    rows = [
        {"date": ln.date, "entry": ln.entry_number, "memo": ln.memo,
         "debit": ln.debit, "credit": ln.credit, "balance": ln.running_balance}
        for ln in gl.lines
    ]
    footer = [{"memo": _l("Closing balance", "الرصيد الختامي", lang), "balance": gl.closing_balance}]
    meta = [(_l("Account", "الحساب", lang), f"{gl.account_code} — {gl.account_name}")]
    if getattr(gl, "party_code", ""):
        party_label = (
            _l("Customer", "العميل", lang) if gl.party_type == "customer"
            else _l("Supplier", "المورد", lang) if gl.party_type == "supplier"
            else _l("Party", "الطرف", lang)
        )
        meta.append((party_label, gl.party_code))
    if period:
        meta.append((_l("Period", "الفترة", lang), period))
    return ReportTable(title=_l("General Ledger", "دفتر الأستاذ", lang),
                       columns=cols, rows=rows, footer=footer, meta=meta, rtl=(lang == "ar"))


def _section(label: str) -> dict:
    return {"label": label, "amount": ""}


def income_statement_table(st, lang: str) -> ReportTable:
    cols = [
        Column("label", _l("Line", "البند", lang)),
        _money("Amount", "القيمة", "amount", lang),
    ]
    rows: list[dict] = [_section(_l("Revenue", "الإيرادات", lang))]
    rows += [{"label": f"{li.account_code} — {li.account_name}", "amount": li.amount} for li in st.revenue]
    rows.append({"label": _l("Total revenue", "إجمالي الإيرادات", lang), "amount": st.total_revenue})
    rows.append(_section(_l("Expenses", "المصروفات", lang)))
    rows += [{"label": f"{li.account_code} — {li.account_name}", "amount": li.amount} for li in st.expenses]
    rows.append({"label": _l("Total expenses", "إجمالي المصروفات", lang), "amount": st.total_expenses})
    footer = [{"label": _l("Net income", "صافي الدخل", lang), "amount": st.net_income}]
    meta = []
    if st.date_from or st.date_to:
        meta.append((_l("Period", "الفترة", lang), f"{st.date_from or '…'} → {st.date_to or '…'}"))
    return ReportTable(title=_l("Income Statement", "قائمة الدخل", lang),
                       columns=cols, rows=rows, footer=footer, meta=meta, rtl=(lang == "ar"))


def balance_sheet_table(bs, lang: str) -> ReportTable:
    cols = [
        Column("label", _l("Line", "البند", lang)),
        _money("Amount", "القيمة", "amount", lang),
    ]
    rows: list[dict] = [_section(_l("Assets", "الأصول", lang))]
    rows += [{"label": f"{li.account_code} — {li.account_name}", "amount": li.amount} for li in bs.assets]
    rows.append({"label": _l("Total assets", "إجمالي الأصول", lang), "amount": bs.total_assets})
    rows.append(_section(_l("Liabilities", "الخصوم", lang)))
    rows += [{"label": f"{li.account_code} — {li.account_name}", "amount": li.amount} for li in bs.liabilities]
    rows.append({"label": _l("Total liabilities", "إجمالي الخصوم", lang), "amount": bs.total_liabilities})
    rows.append(_section(_l("Equity", "حقوق الملكية", lang)))
    rows += [{"label": f"{li.account_code} — {li.account_name}", "amount": li.amount} for li in bs.equity]
    rows.append({"label": _l("Net income", "صافي الدخل", lang), "amount": bs.net_income})
    rows.append({"label": _l("Total equity", "إجمالي حقوق الملكية", lang), "amount": bs.total_equity})
    footer = [{"label": _l("Total liabilities & equity", "إجمالي الخصوم وحقوق الملكية", lang),
               "amount": bs.total_liabilities_and_equity}]
    meta = [(_l("As of", "كما في", lang), bs.as_of)] if bs.as_of else []
    return ReportTable(title=_l("Balance Sheet", "الميزانية العمومية", lang),
                       columns=cols, rows=rows, footer=footer, meta=meta, rtl=(lang == "ar"))


def cash_flow_table(cf, lang: str) -> ReportTable:
    cols = [
        Column("label", _l("Line", "البند", lang)),
        _money("Amount", "القيمة", "amount", lang),
    ]
    rows = [
        {"label": _l("Opening balance", "الرصيد الافتتاحي", lang), "amount": cf.opening_balance},
        {"label": _l("Cash in", "تدفقات داخلة", lang), "amount": cf.cash_in},
        {"label": _l("Cash out", "تدفقات خارجة", lang), "amount": -cf.cash_out},
        {"label": _l("Net change", "صافي التغير", lang), "amount": cf.net_change},
    ]
    footer = [{"label": _l("Closing balance", "الرصيد الختامي", lang), "amount": cf.closing_balance}]
    meta = []
    if cf.date_from or cf.date_to:
        meta.append((_l("Period", "الفترة", lang), f"{cf.date_from or '…'} → {cf.date_to or '…'}"))
    return ReportTable(title=_l("Cash Flow", "التدفقات النقدية", lang),
                       columns=cols, rows=rows, footer=footer, meta=meta, rtl=(lang == "ar"))


def asset_register_table(reg, lang: str) -> ReportTable:
    cols = [
        Column("code", _l("Code", "الرمز", lang)),
        Column("name", _l("Asset", "الأصل", lang)),
        Column("category", _l("Category", "الفئة", lang)),
        Column("acquired", _l("Acquired", "تاريخ الشراء", lang)),
        _money("Cost", "التكلفة", "cost", lang),
        _money("Accum. Depr.", "مجمع الإهلاك", "accumulated", lang),
        _money("Net Book Value", "صافي القيمة الدفترية", "nbv", lang),
    ]
    rows = [
        {"code": r.code, "name": r.name, "category": r.category, "acquired": r.acquisition_date,
         "cost": r.cost_minor, "accumulated": r.accumulated_depreciation_minor,
         "nbv": r.net_book_value_minor}
        for r in reg.rows
    ]
    footer = [{"code": "", "name": _l("Total", "الإجمالي", lang), "category": "", "acquired": "",
               "cost": reg.total_cost, "accumulated": reg.total_accumulated, "nbv": reg.total_nbv}]
    return ReportTable(title=_l("Fixed Asset Register", "سجل الأصول الثابتة", lang),
                       columns=cols, rows=rows, footer=footer, meta=[], rtl=(lang == "ar"))


def built_report_table(built, lang: str) -> ReportTable:
    group_label = _l("Account", "الحساب", lang) if built.group_by == "account" else _l("Period", "الفترة", lang)
    cols = [
        Column("group", group_label),
        _money("Debit", "مدين", "debit", lang),
        _money("Credit", "دائن", "credit", lang),
        _money("Balance", "الرصيد", "balance", lang),
    ]
    rows = [
        {"group": r.group_label, "debit": r.debit, "credit": r.credit, "balance": r.balance}
        for r in built.rows
    ]
    footer = [{"group": _l("Total", "الإجمالي", lang), "debit": built.total_debit,
               "credit": built.total_credit, "balance": built.total_balance}]
    meta = []
    if built.date_from or built.date_to:
        meta.append((_l("Period", "الفترة", lang), f"{built.date_from or '…'} → {built.date_to or '…'}"))
    return ReportTable(title=built.name, columns=cols, rows=rows, footer=footer, meta=meta,
                       rtl=(lang == "ar"))


def budget_vs_actual_table(bva, lang: str) -> ReportTable:
    cols = [
        Column("code", _l("Code", "الرمز", lang)),
        Column("name", _l("Account", "الحساب", lang)),
        _money("Budget", "الموازنة", "budget", lang),
        _money("Actual", "الفعلي", "actual", lang),
        _money("Variance", "الانحراف", "variance", lang),
    ]
    rows = [
        {"code": r.account_code, "name": r.account_name,
         "budget": r.budget_minor, "actual": r.actual_minor, "variance": r.variance_minor}
        for r in bva.rows
    ]
    footer = [{"code": "", "name": _l("Total", "الإجمالي", lang),
               "budget": bva.total_budget, "actual": bva.total_actual, "variance": bva.total_variance}]
    meta = [(_l("Budget", "الموازنة", lang), f"{bva.budget_name} ({bva.fiscal_year_code})")]
    if bva.period_code:
        meta.append((_l("Period", "الفترة", lang), bva.period_code))
    return ReportTable(title=_l("Budget vs Actual", "الموازنة مقابل الفعلي", lang),
                       columns=cols, rows=rows, footer=footer, meta=meta, rtl=(lang == "ar"))


def vat_return_table(vr, lang: str) -> ReportTable:
    cols = [
        Column("label", _l("Line", "البند", lang)),
        _money("Amount", "القيمة", "amount", lang),
    ]
    rows = [
        {"label": _l("Output VAT (sales)", "ضريبة المخرجات (مبيعات)", lang), "amount": vr.output_vat},
        {"label": _l("Reversals (returns)", "مرتجعات", lang), "amount": -vr.reversals},
        {"label": _l("Input VAT (purchases)", "ضريبة المدخلات (مشتريات)", lang), "amount": -vr.input_vat},
        {"label": _l("Input reversals", "مرتجعات المدخلات", lang), "amount": vr.input_reversals},
    ]
    footer = [{"label": _l("Net VAT payable", "صافي الضريبة المستحقة", lang), "amount": vr.net_payable}]
    meta = [(_l("Period", "الفترة", lang), f"{vr.start_date} → {vr.end_date}")]
    return ReportTable(title=_l("VAT Return", "الإقرار الضريبي", lang),
                       columns=cols, rows=rows, footer=footer, meta=meta, rtl=(lang == "ar"))
