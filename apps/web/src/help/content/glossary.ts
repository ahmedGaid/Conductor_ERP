// Glossary "المصطلحات" — rendered from a single data file whose entries mirror Identity System
// §6.1 one-to-one (FILE_15 Task B). A drift here is a bug: adding, renaming, or dropping a term
// must happen in the lexicon table first, then here — never invent a second Arabic word for a
// concept that already has one.
import type { GlossaryEntry } from "../types";

export const GLOSSARY: GlossaryEntry[] = [
  {
    term: { ar: "فاتورة", en: "Invoice" },
    desc: { ar: "المستند الذي يطلب فيه البائع المبلغ المستحق من العميل.", en: "The document a seller uses to request the amount owed by a customer." },
  },
  {
    term: { ar: "أمر بيع", en: "Sales order" },
    desc: { ar: "طلب عميل مؤكَّد يبدأ مسار التسليم والفوترة.", en: "A confirmed customer request that starts the delivery-and-invoicing path." },
  },
  {
    term: { ar: "عرض سعر", en: "Quotation" },
    desc: { ar: "سعر مقترح للعميل قبل تحويله إلى أمر بيع فعلي.", en: "A proposed price for a customer, before it becomes an actual sales order." },
  },
  {
    term: { ar: "أمر شراء", en: "Purchase order" },
    desc: { ar: "طلب شراء مؤكَّد يُرسل إلى المورد.", en: "A confirmed purchase request sent to a supplier." },
  },
  {
    term: { ar: "طلب شراء", en: "Purchase request" },
    desc: { ar: "طلب داخلي للشراء قبل موافقته وتحويله لأمر شراء.", en: "An internal request to buy, before it's approved and converted to a purchase order." },
  },
  {
    term: { ar: "عميل", en: "Customer" },
    desc: { ar: "جهة تشتري من الشركة.", en: "A party who buys from the company." },
  },
  {
    term: { ar: "مورد", en: "Supplier / Vendor" },
    desc: { ar: "جهة تبيع للشركة.", en: "A party who sells to the company." },
  },
  {
    term: { ar: "المخزون", en: "Inventory / Stock" },
    desc: { ar: "الكمية المتاحة من الأصناف حاليًا.", en: "The quantity of items currently on hand." },
  },
  {
    term: { ar: "البضاعة", en: "Goods" },
    desc: { ar: "الأصناف المادية وقت تسليمها أو استلامها فعليًا.", en: "The physical items at the moment they're delivered or received." },
  },
  {
    term: { ar: "مخزن", en: "Warehouse" },
    desc: { ar: "المكان الذي تُخزَّن فيه البضاعة.", en: "The physical location where goods are stored." },
  },
  {
    term: { ar: "صنف", en: "Item / Product" },
    desc: { ar: "الشيء الذي تبيعه أو تشتريه الشركة.", en: "The thing the company sells or buys." },
  },
  {
    term: { ar: "حساب", en: "Account (GL)" },
    desc: { ar: "بند في دليل الحسابات تُسجَّل فيه الحركات المالية.", en: "A line in the chart of accounts that financial movements post to." },
  },
  {
    term: { ar: "قيد يومية", en: "Journal entry" },
    desc: { ar: "تسجيل محاسبي متوازن (مدين = دائن) لحركة مالية.", en: "A balanced accounting record (debit = credit) of a financial movement." },
  },
  {
    term: { ar: "ميزان المراجعة", en: "Trial balance" },
    desc: { ar: "كشف يجمع أرصدة كل الحسابات للتأكد من توازن الدفاتر.", en: "A report of every account's balance, used to confirm the books balance." },
  },
  {
    term: { ar: "دفتر الأستاذ", en: "Ledger" },
    desc: { ar: "كل القيود التي كوّنت رصيد حساب معيّن، بالترتيب.", en: "Every entry, in order, that built a given account's balance." },
  },
  {
    term: { ar: "دفعة / سداد", en: "Payment" },
    desc: { ar: "تحصيل أو دفع مبلغ مقابل فاتورة.", en: "Collecting or paying an amount against an invoice." },
  },
  {
    term: { ar: "سداد جزئي", en: "Partial payment" },
    desc: { ar: "دفع أقل من كامل المبلغ المستحق.", en: "Paying less than the full outstanding amount." },
  },
  {
    term: { ar: "المبالغ المستحقة (لنا)", en: "Receivables" },
    desc: { ar: "ما هو مستحق للشركة من عملائها.", en: "What customers owe the company." },
  },
  {
    term: { ar: "موافقة", en: "Approval" },
    desc: { ar: "قرار بشري يُوافَق فيه على مستند قبل تنفيذه.", en: "A human decision approving a document before it proceeds." },
  },
  {
    term: { ar: "مسودة", en: "Draft" },
    desc: { ar: "مستند لم يُعتمد أو يُرسل بعد، ويمكن تعديله بحرية.", en: "A document not yet finalized or sent — freely editable." },
  },
  {
    term: { ar: "ترحيل", en: "Post (to ledger)" },
    desc: { ar: "تثبيت قيد في دفتر الأستاذ بعد التأكد من توازنه.", en: "Committing an entry to the ledger once it's confirmed balanced." },
  },
  {
    term: { ar: "تسوية", en: "Reconcile" },
    desc: { ar: "مطابقة سجلات النظام بكشف حساب خارجي (بنكي مثلًا).", en: "Matching the system's records against an outside statement (a bank statement, for example)." },
  },
  {
    term: { ar: "مطابقة", en: "Match" },
    desc: { ar: "ربط حركتين ماليتين ببعضهما، كخطوة ضمن التسوية.", en: "Linking two financial movements together, as one step within reconciling." },
  },
  {
    term: { ar: "فاتورة إلكترونية", en: "e-invoice" },
    desc: { ar: "فاتورة مُجهَّزة بالشكل الذي تطلبه مصلحة الضرائب المصرية. الإرسال إليها غير موصول بعد.", en: "An invoice prepared in the form the Egyptian Tax Authority requires. Filing to the Authority is not connected yet." },
  },
  {
    term: { ar: "ملاحظات", en: "Notes" },
    desc: { ar: "نص حر يُضاف على أي سجل لتوضيح تفاصيل إضافية.", en: "Free text added to a record to note extra detail." },
  },
  {
    term: { ar: "فرصة", en: "Opportunity" },
    desc: { ar: "صفقة محتملة مع عميل، قبل تحوّلها لبيع فعلي أو خسارتها.", en: "A potential deal with a customer, before it's won or lost." },
  },
  {
    term: { ar: "المالية", en: "Accounting module" },
    desc: { ar: "القسم الذي يضم كل شاشات المحاسبة والتقارير المالية.", en: "The section holding every accounting screen and financial report." },
  },
  {
    term: { ar: "المساعد الذكي", en: "AI assistant" },
    desc: { ar: "المساعد الذي يجيب عن أسئلة بياناتك ويقترح إجراءات تُوافَق قبل تنفيذها.", en: "The assistant that answers questions about your data and proposes actions you approve before they happen." },
  },
  {
    term: { ar: "قاعدة المعرفة", en: "Knowledge base" },
    desc: { ar: "المستندات التي يبحث فيها المساعد الذكي ليجيبك.", en: "The documents the AI assistant searches to answer you." },
  },
  {
    term: { ar: "طريقة عرض", en: "Saved view" },
    desc: { ar: "مجموعة فلاتر محفوظة باسم لإعادة استخدامها على قائمة.", en: "A named, saved set of filters you can reapply to a list." },
  },
  {
    term: { ar: "سجل النشاط", en: "Activity timeline" },
    desc: { ar: "كل ما حدث لسجل معيّن، بترتيب زمني.", en: "Everything that happened to a given record, in time order." },
  },
  {
    term: { ar: "إسناد", en: "Assign (a role)" },
    desc: { ar: "ربط مستخدم بدور يحدد صلاحياته.", en: "Linking a user to a role that determines their permissions." },
  },
  {
    term: { ar: "متأخر", en: "Overdue" },
    desc: { ar: "مستند مالي تجاوز تاريخ استحقاقه دون تحصيل أو سداد.", en: "A money document past its due date without being collected or paid." },
  },
  {
    term: { ar: "يستحق قريبًا", en: "Due soon" },
    desc: { ar: "مستند مالي يقترب موعد استحقاقه.", en: "A money document nearing its due date." },
  },
  {
    term: { ar: "المسؤول", en: "Owner" },
    desc: { ar: "الموظف المكلَّف بمتابعة سجل معيّن (فرصة أو تذكرة مثلًا).", en: "The staff member responsible for following up a given record (an opportunity or ticket, for example)." },
  },
  {
    term: { ar: "ويب هوك", en: "Webhook" },
    desc: { ar: "اشتراك يُبلِّغ نظامًا خارجيًا تلقائيًا عند حدوث شيء معيّن.", en: "A subscription that automatically notifies an outside system when something happens." },
  },
  {
    term: { ar: "الحقول المخصّصة", en: "Custom field" },
    desc: { ar: "حقل إضافي يُعرِّفه مدير النظام على العملاء أو الأصناف.", en: "An extra field an admin defines on customers or items." },
  },
  {
    term: { ar: "مفتاح API", en: "API key" },
    desc: { ar: "بيانات اعتماد لربط نظام خارجي بدور صلاحيات محدد.", en: "A credential that links an outside system to one bound permission role." },
  },
];
