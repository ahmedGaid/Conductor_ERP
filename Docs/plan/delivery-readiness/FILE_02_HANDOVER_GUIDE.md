# Conductor — How to Run It (Handover Guide) / دليل التشغيل

One page. AR block first (product default language), EN block below.

---

## دليل التشغيل — بالعربية

### تسجيل الدخول
افتح رابط النظام في المتصفح. أدخل اسم المستخدم وكلمة المرور. الواجهة عربية افتراضيًا (من اليمين
لليسار)؛ يمكن التبديل للإنجليزية من شريط الأوامر أعلى الشاشة.

### الإعداد الأول (مرة واحدة عند التسليم)
1. عيّن كلمة مرور جديدة لحساب المدير (لا تُبقِ كلمة المرور الافتراضية).
2. من **الإعدادات ← بيانات المنشأة**: اسم الشركة، الرقم الضريبي، الدولة، لغة الواجهة الافتراضية.
3. من **الإدارة ← المستخدمون**: أضف مستخدمي الشركة وحدد الدور لكل واحد (مدير نظام / مدير فرع /
   محاسب / مراجع).
4. راجع دليل الحسابات ودورة السنة المالية (تُنشأ تلقائيًا عند التثبيت بحسابات أساسية فارغة).
5. الفوترة الإلكترونية (ETA): تحتاج بيانات اعتماد حقيقية من مصلحة الضرائب — لم تُفعَّل بعد،
   راجع قائمة "غير مكتمل" أدناه.

### الاستخدام اليومي — المسارات الأساسية
- **المبيعات:** عميل ← طلب جديد ← تأكيد ← تسليم (يخصم من المخزون تلقائيًا) ← إصدار فاتورة ←
  تسجيل تحصيل الدفعة.
- **المشتريات:** طلب شراء ← موافقة ← تحويل لأمر شراء ← تأكيد ← استلام البضاعة ← فاتورة المورد
  (تُطابق تلقائيًا مع الكمية المستلمة) ← تسجيل الدفع.
- **المخزون:** حركات المخزون والجرد الدوري من قائمة المخزون؛ الأرصدة تتحدث تلقائيًا مع كل عملية بيع
  أو استلام.
- **المحاسبة:** كل عملية بيع/شراء تُنشئ قيدًا محاسبيًا تلقائيًا. القيود اليدوية من "قيد جديد"،
  ولا يُقبل القيد إلا إذا كان متوازنًا (مدين = دائن). التقارير (ميزان المراجعة، قائمة الدخل،
  الميزانية) من قائمة المحاسبة.
- **العملاء المحتملون (CRM):** الفرصة ← تحويل لعميل عند الفوز؛ العميل المحتمل يُسجَّل من "عملاء
  محتملون جدد".
- **ملاحظة مهمة:** التحصيل وتسجيل دفع المورد يسجلان **كامل المبلغ المستحق دفعة واحدة** — لا يوجد
  حاليًا خيار لتسجيل دفعة جزئية من الواجهة.

### تنبيه أمني
لا تُشارك كلمة مرور المدير. كل مستخدم يجب أن يملك حسابه الخاص بالدور المناسب لصلاحياته.

---

## English — How to Run Conductor

### Login
Open the system URL in a browser. Enter username/password. Arabic/RTL is the default; switch to
English from the command bar (⌘K) at the top.

### First-time setup (once, at handover)
1. Set a new password for the admin account (do not keep the default).
2. **Settings → Organization**: company name, VAT number, country, default UI language.
3. **Admin → Users**: add each staff member and assign a role (System Admin / Branch Manager /
   Accountant / Auditor).
4. Review the chart of accounts and fiscal year (auto-created empty on install — no demo clutter).
5. E-Invoice (ETA): requires real Egyptian Tax Authority credentials — not yet enabled; see
   "Not included" below.

### Daily flows
- **Sales:** pick customer → new order → confirm → deliver (auto stock issue) → invoice →
  collect payment.
- **Purchasing:** requisition → approve → convert to PO → confirm → receive goods → supplier
  invoice (auto 3-way match against received qty) → register payment.
- **Inventory:** stock movements and cycle counts from the Inventory menu; balances update
  automatically on every sale/receipt.
- **Accounting:** every sale/purchase auto-posts a journal entry. Manual entries via "New Journal"
  — only accepted if balanced (debit = credit). Reports (trial balance, P&L, balance sheet) live
  under Accounting.
- **CRM:** opportunity → convert to customer on win; new leads logged under Leads.
- **Important:** collect/payment actions settle the **full outstanding amount in one click** — no
  partial-payment option in the UI yet.

### Security note
Never share the admin password. Every staff member should have their own account scoped to their
role.
