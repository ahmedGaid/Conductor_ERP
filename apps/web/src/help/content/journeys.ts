// Task-based journeys for the standalone User Guide (`/help/guide`), distinct from the per-page
// contextual `HelpGuide`s in registry.ts. A journey follows the user's real-world goal across
// however many screens it takes, written ar-first then en to match (FILE_15). Ten journeys cover
// the daily-use core; extend here as new task-critical flows land — never invent a second page for
// the same goal.
import type { Journey } from "../types";

export const JOURNEYS: Journey[] = [
  {
    id: "first-invoice",
    title: { ar: "إصدار أول فاتورة", en: "Create your first invoice" },
    summary: {
      ar: "من عميل جديد إلى فاتورة مُرسلة — المسار الكامل.",
      en: "From a new customer to an issued invoice — the full path.",
    },
    steps: [
      { ar: "المبيعات ← العملاء ← أضف عميلًا جديدًا (الاسم، الرقم الضريبي إن وجد).", en: "Sales → Customers → add a new customer (name, VAT number if any)." },
      { ar: "المبيعات ← طلب جديد ← اختر العميل والأصناف والكميات ← تأكيد.", en: "Sales → New order → pick the customer, items, and quantities → confirm." },
      { ar: "من الطلب المؤكَّد: تسليم (يخصم من المخزون تلقائيًا) ← إصدار فاتورة.", en: "From the confirmed order: deliver (auto stock issue) → issue invoice." },
      { ar: "الفاتورة تُنشئ قيدًا محاسبيًا تلقائيًا — لا حاجة لقيد يدوي.", en: "The invoice posts its journal entry automatically — no manual entry needed." },
      { ar: "لتحصيل المبلغ: من الفاتورة أو الطلب ← تسجيل تحصيل، كاملًا أو جزئيًا.", en: "To collect payment: from the invoice or order → record collection, in full or partial." },
    ],
    pitfalls: [
      {
        problem: { ar: "الطلب لا يظهر خيار \"تسليم\".", en: "The order has no \"deliver\" option." },
        fix: { ar: "الطلب يجب أن يكون في حالة \"مؤكَّد\" أولًا — راجع حالته أعلى الصفحة.", en: "The order must be confirmed first — check its status at the top of the page." },
      },
      {
        problem: { ar: "الكمية المتاحة في المخزون أقل من المطلوب.", en: "Available stock is less than the ordered quantity." },
        fix: { ar: "سجّل استلام بضاعة إضافية من المخزون، أو عدّل الكمية في الطلب.", en: "Receive more stock first, or reduce the quantity on the order." },
      },
    ],
    related: [{ to: "/sales/orders/new", label: { ar: "طلب بيع جديد", en: "New sales order" } }],
  },
  {
    id: "receive-goods",
    title: { ar: "استلام البضاعة", en: "Receive goods" },
    summary: {
      ar: "من أمر الشراء إلى زيادة المخزون ومطابقة فاتورة المورد.",
      en: "From a purchase order to increased stock and a matched supplier invoice.",
    },
    steps: [
      { ar: "المشتريات ← أمر شراء (جديد أو من طلب شراء مُعتمد) ← تأكيد.", en: "Purchasing → purchase order (new, or from an approved request) → confirm." },
      { ar: "من الأمر المؤكَّد: استلام البضاعة — أدخل الكمية المستلمة فعليًا لكل صنف.", en: "From the confirmed order: receive goods — enter the quantity actually received per item." },
      { ar: "الاستلام يزيد المخزون فورًا في المخزن المحدَّد.", en: "Receiving increases stock immediately in the chosen warehouse." },
      { ar: "فاتورة المورد تُطابَق تلقائيًا مع الكمية المستلمة (مطابقة ثلاثية).", en: "The supplier invoice auto-matches against the received quantity (3-way match)." },
      { ar: "أي فرق بين المطلوب والمستلم يظهر في تفاصيل الأمر — راجعه قبل تسجيل الدفع.", en: "Any gap between ordered and received shows on the order detail — review before recording payment." },
    ],
    pitfalls: [
      {
        problem: { ar: "الكمية المستلمة أقل من كمية الأمر.", en: "The received quantity is less than the order quantity." },
        fix: { ar: "استلام جزئي مسموح — أكمل الباقي في استلام لاحق لنفس الأمر.", en: "Partial receipt is allowed — receive the remainder later against the same order." },
      },
    ],
    related: [{ to: "/purchasing/orders/new", label: { ar: "أمر شراء جديد", en: "New purchase order" } }],
  },
  {
    id: "record-payment",
    title: { ar: "تسجيل دفعة", en: "Record a payment" },
    summary: {
      ar: "تحصيل من عميل أو سداد لمورد — كاملًا أو على دفعات.",
      en: "Collect from a customer or pay a supplier — in full or in parts.",
    },
    steps: [
      { ar: "افتح الفاتورة (بيع) أو فاتورة المورد (شراء) — ستجد رصيدها المستحق أعلاها.", en: "Open the invoice (sale) or supplier invoice (purchase) — its outstanding balance shows at the top." },
      { ar: "تسجيل تحصيل / تسجيل دفع ← أدخل المبلغ.", en: "Record collection / record payment → enter the amount." },
      { ar: "لسداد جزء فقط: أدخل مبلغًا أقل من المستحق — الرصيد المتبقي يظل ظاهرًا للمتابعة.", en: "For a partial payment: enter less than the full amount — the remaining balance stays visible to follow up." },
      { ar: "كل دفعة تُنشئ قيد محاسبي تلقائيًا وتُحدِّث رصيد العميل/المورد فورًا.", en: "Every payment posts its journal entry automatically and updates the customer/supplier balance right away." },
    ],
    pitfalls: [
      {
        problem: { ar: "أُدخل مبلغ أكبر من المستحق بالخطأ.", en: "Entered an amount larger than what's owed by mistake." },
        fix: { ar: "النظام يرفض تسجيل مبلغ يتجاوز الرصيد المستحق — أعد إدخال المبلغ الصحيح.", en: "The system refuses a payment above the outstanding balance — re-enter the correct amount." },
      },
    ],
    related: [{ to: "/sales", label: { ar: "أوامر البيع", en: "Sales orders" } }],
  },
  {
    id: "opening-balances",
    title: { ar: "أرصدة بداية الشهر (الافتتاحية)", en: "Month-start opening balances" },
    summary: {
      ar: "تسجيل الأرصدة الافتتاحية للحسابات عند بداية التشغيل أو دورة جديدة.",
      en: "Recording opening account balances at go-live or the start of a new period.",
    },
    steps: [
      { ar: "المحاسبة ← دليل الحسابات — تأكد من وجود كل حساب ستُدخل له رصيدًا.", en: "Accounting → chart of accounts — confirm every account you'll enter a balance for exists." },
      { ar: "المحاسبة ← قيد جديد ← أدخل كل حساب بمبلغه المدين أو الدائن كما في الأرصدة الفعلية.", en: "Accounting → new journal entry → enter each account with its actual debit or credit balance." },
      { ar: "القيد لا يُقبل إلا إذا كان متوازنًا تمامًا (إجمالي المدين = إجمالي الدائن).", en: "The entry is only accepted if it balances exactly (total debit = total credit)." },
      { ar: "بعد الترحيل، راجع ميزان المراجعة للتأكد من مطابقة الأرصدة.", en: "After posting, check the trial balance to confirm the balances match." },
    ],
    pitfalls: [
      {
        problem: { ar: "القيد غير متوازن ولا يمكن ترحيله.", en: "The entry doesn't balance and won't post." },
        fix: { ar: "راجع كل سطر — الفرق بين المدين والدائن يظهر أسفل القيد قبل الترحيل.", en: "Review every line — the debit/credit difference shows below the entry before you post." },
      },
    ],
    related: [
      { to: "/accounting/journals/new", label: { ar: "قيد يومية جديد", en: "New journal entry" } },
      { to: "/accounting", label: { ar: "دليل الحسابات", en: "Chart of accounts" } },
    ],
  },
  {
    id: "trial-balance",
    title: { ar: "تشغيل ميزان المراجعة", en: "Run the trial balance" },
    summary: {
      ar: "التأكد من توازن الدفاتر لأي فترة، ومتابعة أي فرق.",
      en: "Confirming the books balance for any period, and chasing down a mismatch.",
    },
    steps: [
      { ar: "المحاسبة ← ميزان المراجعة ← اختر الفترة (الشهر أو السنة المالية).", en: "Accounting → trial balance → choose the period (month or fiscal year)." },
      { ar: "كل حساب يظهر برصيده المدين أو الدائن حتى نهاية الفترة.", en: "Every account shows its debit or credit balance as of the period end." },
      { ar: "إجمالي المدين والدائن يجب أن يتساويا — هذا ما يعنيه \"توازن\" الدفاتر.", en: "Total debits and total credits must be equal — that's what \"balanced\" books means." },
      { ar: "لأي رقم يبدو غير متوقَّع، افتح دفتر الأستاذ لنفس الحساب لرؤية كل القيود التي كوّنته.", en: "For any figure that looks off, open that account's general ledger to see every entry that built it." },
    ],
    related: [
      { to: "/accounting/trial-balance", label: { ar: "ميزان المراجعة", en: "Trial balance" } },
      { to: "/accounting/general-ledger", label: { ar: "دفتر الأستاذ", en: "General ledger" } },
    ],
  },
  {
    id: "einvoice-submission",
    title: { ar: "تجهيز الفاتورة الإلكترونية (منظومة الفوترة)", en: "Preparing an e-invoice (ETA)" },
    summary: {
      ar: "تجهيز فاتورة بيع بشكل الفوترة الإلكترونية المصرية ومتابعتها. الإرسال إلى المصلحة غير موصول بعد.",
      en: "Preparing a sales invoice in Egyptian e-invoicing form and tracking it. Filing to the Authority is not connected yet.",
    },
    steps: [
      { ar: "بعد إصدار فاتورة بيع، تظهر في قائمة الفوترة الإلكترونية كمسودة.", en: "After issuing a sales invoice, it appears in the e-invoicing list as a draft." },
      { ar: "من القائمة: اضغط \"تجهيز للإرسال\" — تصبح الحالة \"مُجهَّزة\" ويُنشأ لها مرجع محلي.", en: "From the list: click \"Prepare for filing\" — the status becomes \"Prepared\" and a local reference is generated." },
      { ar: "قدّم الفاتورة لمصلحة الضرائب بطريقتك المعتادة — النظام لا يرسلها نيابة عنك بعد.", en: "File the invoice with the Tax Authority the way you do today — the system does not send it for you yet." },
    ],
    pitfalls: [
      {
        problem: { ar: "توقّع أن \"مُجهَّزة\" تعني أن المصلحة استلمت الفاتورة.", en: "Assuming \"Prepared\" means the Authority received the invoice." },
        fix: { ar: "لا تعني ذلك. المرجع يُنشئه النظام محليًا، والتقديم للمصلحة ما زال يدويًا حتى يتم توصيل الخدمة.", en: "It does not. The reference is generated locally, and filing stays manual until the connection is set up." },
      },
    ],
    related: [{ to: "/einvoice", label: { ar: "الفوترة الإلكترونية", en: "E-invoicing" } }],
  },
  {
    id: "add-user-role",
    title: { ar: "إضافة مستخدم ودور", en: "Add a user and role" },
    summary: {
      ar: "منح موظف جديد حسابًا خاصًا بصلاحيات تناسب عمله.",
      en: "Giving a new staff member their own account, scoped to their job.",
    },
    steps: [
      { ar: "الإدارة ← المستخدمون ← أضف مستخدمًا جديدًا (الاسم، اسم الدخول).", en: "Admin → Users → add a new user (name, login)." },
      { ar: "اختر الدور المناسب: مدير نظام / مدير فرع / محاسب / مراجع.", en: "Assign the right role: System Admin / Branch Manager / Accountant / Auditor." },
      { ar: "كل دور يحدد الصفحات والإجراءات المتاحة للمستخدم — راجع الإدارة ← الأدوار لمعرفة تفاصيل كل دور.", en: "Each role determines the pages and actions available to that user — check Admin → Roles for the detail of each." },
      { ar: "المستخدم يسجّل الدخول بكلمة مرور خاصة به منذ اليوم الأول — لا تُشارك حساب المدير أبدًا.", en: "The user signs in with their own password from day one — never share the admin account." },
    ],
    related: [
      { to: "/admin/users", label: { ar: "المستخدمون", en: "Users" } },
      { to: "/admin/roles", label: { ar: "الأدوار", en: "Roles" } },
    ],
  },
  {
    id: "take-backup",
    title: { ar: "أخذ نسخة احتياطية", en: "Take a backup" },
    summary: {
      ar: "حماية بيانات الشركة من الفقد — إجراء تشغيلي، ليس زرًا في الواجهة بعد.",
      en: "Protecting the company's data from loss — an operations task, not yet a button in the app.",
    },
    steps: [
      { ar: "النسخ الاحتياطي حاليًا مسؤولية من يدير الخادم (فريقك التقني أو مزوّد الاستضافة)، وليس زرًا في الواجهة.", en: "Backups today are the responsibility of whoever administers the server (your IT team or hosting provider), not a button in the app." },
      { ar: "اتفق مع المسؤول التقني على جدول نسخ احتياطي دوري (يوميًا على الأقل) لقاعدة بيانات النظام.", en: "Agree with your technical contact on a recurring backup schedule (at least daily) for the system database." },
      { ar: "قبل أي تحديث كبير للنظام، تأكد من وجود نسخة حديثة أولًا.", en: "Before any major system upgrade, confirm a recent backup exists first." },
    ],
  },
  {
    id: "fix-rejected-approval",
    title: { ar: "معالجة موافقة مرفوضة", en: "Fix a rejected approval" },
    summary: {
      ar: "متى تُرفض موافقة على مستند، وكيف تُصحِّحه وتعيد تقديمه.",
      en: "When a document's approval is rejected, and how to fix and resubmit it.",
    },
    steps: [
      { ar: "افتح المستند نفسه (طلب شراء، عرض سعر، أو أي مستند يمر بموافقة) — سبب الرفض يظهر في سجل النشاط أسفل الصفحة.", en: "Open the document itself (purchase request, quotation, or any document that goes through approval) — the rejection reason shows in the activity timeline at the bottom of the page." },
      { ar: "إن كانت الموافقة عبر مسار عمل (Workflow)، افتح سجل التنفيذ من المسار لرؤية الخطوة التي رفضت وسببها بالتفصيل.", en: "If the approval runs through a workflow, open its execution log from the workflow to see exactly which step rejected it and why." },
      { ar: "صحّح المستند (المبلغ، الصنف، أو أي بيان خاطئ) ثم أعد تقديمه للموافقة من جديد.", en: "Fix the document (the amount, the item, or whatever was wrong), then resubmit it for approval." },
      { ar: "الرفض ليس خطأً تقنيًا — هو قرار بشري يظهر سببه دائمًا، بلا رسائل خطأ غامضة.", en: "A rejection isn't a technical error — it's a human decision that always states its reason, never a vague error message." },
    ],
    related: [{ to: "/workflows", label: { ar: "مسارات العمل", en: "Workflows" } }],
  },
  {
    id: "ask-assistant-safely",
    title: { ar: "استخدام المساعد الذكي بأمان", en: "Ask the assistant safely" },
    summary: {
      ar: "ما يفعله المساعد الذكي، وما لا يفعله من تلقاء نفسه.",
      en: "What the AI assistant does, and what it never does on its own.",
    },
    steps: [
      { ar: "افتح المساعد الذكي (⌘J أو من القائمة) واسأل بلغتك الطبيعية — عربي أو إنجليزي.", en: "Open the assistant (⌘J or from the menu) and ask in plain language — Arabic or English." },
      { ar: "المساعد يقرأ بيانات شركتك ليجيب، لكنه لا يُنشئ أو يعدّل أي مستند دون تأكيدك الصريح.", en: "The assistant reads your company's data to answer, but never creates or edits a document without your explicit confirmation." },
      { ar: "أي إجراء يقترحه المساعد (مثل إنشاء فاتورة) يظهر كمسودة تراجعها وتوافق عليها أولًا.", en: "Any action the assistant proposes (like creating an invoice) shows as a draft you review and approve first." },
      { ar: "لا تُدخل بيانات حساسة (كلمات مرور، أرقام بطاقات) في المحادثة — المساعد لا يحتاجها أبدًا.", en: "Never type sensitive data (passwords, card numbers) into the chat — the assistant never needs it." },
    ],
    related: [{ to: "/assistant", label: { ar: "المساعد الذكي", en: "AI assistant" } }],
  },
];

export function getJourney(id: string): Journey | undefined {
  return JOURNEYS.find((j) => j.id === id);
}
