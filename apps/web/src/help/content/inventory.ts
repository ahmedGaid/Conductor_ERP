import type { HelpGuide } from "../types";

export const stockOnHandGuide: HelpGuide = {
  title: { en: "Stock on hand", ar: "الأرصدة المتاحة" },
  purpose: {
    en: "See how much of each item you have, in which warehouse, and what it's worth right now.",
    ar: "اطّلع على كمية كل صنف، وفي أي مستودع، وقيمته الآن.",
  },
  howItWorks: {
    en: "Quantities and values update automatically as you receive, issue, and transfer stock. Value is tracked using weighted-average cost, so the figure here always matches the Inventory account in accounting.",
    ar: "تتحدّث الكميات والقيم تلقائياً مع الاستلام والصرف والتحويل. تُحتسب القيمة بمتوسط التكلفة المرجّح، لذا يطابق الرقم هنا دائماً حساب المخزون في المحاسبة.",
  },
  tasks: [
    {
      name: { en: "Check an item's stock", ar: "افحص رصيد صنف" },
      steps: [
        { en: "Find the item in the list (or search).", ar: "جد الصنف في القائمة (أو ابحث)." },
        { en: "Read its quantity and value per warehouse.", ar: "اقرأ كميته وقيمته لكل مستودع." },
      ],
    },
  ],
  related: [
    { to: "/inventory/movements", label: { en: "Stock movements", ar: "حركات المخزون" } },
    { to: "/inventory/items", label: { en: "Items", ar: "الأصناف" } },
  ],
};

export const itemsGuide: HelpGuide = {
  title: { en: "Items", ar: "الأصناف" },
  purpose: {
    en: "The catalogue of products and materials you buy, sell, or store.",
    ar: "فهرس المنتجات والمواد التي تشتريها أو تبيعها أو تخزّنها.",
  },
  howItWorks: {
    en: "Each item has a unique SKU (code) used everywhere else — on sales orders, purchases, and stock moves. Set it up once here.",
    ar: "لكل صنف رمز فريد (SKU) يُستخدم في كل مكان آخر — في طلبات المبيعات والمشتريات وحركات المخزون. هيّئه هنا مرة واحدة.",
  },
  tasks: [
    {
      name: { en: "Add an item", ar: "أضف صنفاً" },
      steps: [
        { en: "Fill the form: SKU, name, category.", ar: "املأ النموذج: الرمز، الاسم، الفئة." },
        { en: "Save — it's now selectable on orders and movements.", ar: "احفظ — صار قابلاً للاختيار في الطلبات والحركات." },
      ],
    },
  ],
  tips: [
    { en: "Choose clear, stable SKUs — they're hard to change once used in transactions.", ar: "اختر رموزاً واضحة وثابتة — يصعب تغييرها بعد استخدامها في المعاملات." },
  ],
  related: [
    { to: "/inventory/warehouses", label: { en: "Warehouses", ar: "المستودعات" } },
    { to: "/inventory", label: { en: "Stock on hand", ar: "الأرصدة المتاحة" } },
  ],
};

export const warehousesGuide: HelpGuide = {
  title: { en: "Warehouses", ar: "المستودعات" },
  purpose: {
    en: "The physical locations where you keep stock — a main store, a branch, a van.",
    ar: "المواقع المادية التي تحفظ فيها المخزون — مخزن رئيسي، فرع، سيارة توزيع.",
  },
  howItWorks: {
    en: "Each warehouse has a code. Stock is counted per warehouse, so you always know what's where, and you can transfer between them.",
    ar: "لكل مستودع رمز. يُحتسب المخزون لكل مستودع، فتعرف دائماً ما الموجود وأين، ويمكنك التحويل بينها.",
  },
  related: [
    { to: "/inventory/movements", label: { en: "Stock movements", ar: "حركات المخزون" } },
  ],
};

export const stockMovementGuide: HelpGuide = {
  title: { en: "Stock movement", ar: "حركة المخزون" },
  purpose: {
    en: "Record stock coming in (receive), going out (issue), or moving between warehouses (transfer).",
    ar: "سجّل دخول المخزون (استلام)، أو خروجه (صرف)، أو نقله بين المستودعات (تحويل).",
  },
  howItWorks: {
    en: "Pick the movement type, the item, the warehouse(s) and quantity. Receives and issues automatically post the matching accounting entry; transfers move stock without touching the books.",
    ar: "اختر نوع الحركة والصنف والمستودع(ات) والكمية. الاستلام والصرف يُرحّلان القيد المحاسبي تلقائياً؛ والتحويل ينقل المخزون دون المساس بالدفاتر.",
  },
  sections: [
    {
      heading: { en: "Movement types", ar: "أنواع الحركة" },
      items: [
        { term: { en: "Receive", ar: "استلام" }, desc: { en: "Stock in (e.g. a delivery). Optionally tag a batch number and expiry.", ar: "إدخال مخزون (مثل توريد). يمكن وسم رقم تشغيلة وتاريخ صلاحية." } },
        { term: { en: "Issue", ar: "صرف" }, desc: { en: "Stock out at weighted-average cost.", ar: "إخراج مخزون بمتوسط التكلفة المرجّح." } },
        { term: { en: "Transfer", ar: "تحويل" }, desc: { en: "Move between warehouses; no financial effect.", ar: "نقل بين المستودعات؛ دون أثر مالي." } },
      ],
    },
  ],
  mistakes: [
    { en: "You can't issue more than you have — the system blocks an oversell.", ar: "لا يمكنك صرف أكثر مما لديك — يمنع النظام البيع الزائد." },
  ],
  related: [
    { to: "/inventory", label: { en: "Stock on hand", ar: "الأرصدة المتاحة" } },
    { to: "/inventory/batches", label: { en: "Batches", ar: "التشغيلات" } },
  ],
};

export const stockCountsGuide: HelpGuide = {
  title: { en: "Stock counts", ar: "الجرد" },
  purpose: {
    en: "Do a physical count and let the system fix any difference between the shelf and the books.",
    ar: "نفّذ جرداً فعلياً ودع النظام يصحّح أي فرق بين الرفّ والدفاتر.",
  },
  howItWorks: {
    en: "Start a count (it snapshots the system quantities), enter what you actually counted, then post it. The system books an adjustment for each difference so stock value and the ledger stay in step.",
    ar: "ابدأ جرداً (يأخذ لقطة لكميات النظام)، أدخل ما عددته فعلاً، ثم رحّله. يقيّد النظام تسوية لكل فرق ليبقى قيمة المخزون والدفتر متطابقين.",
  },
  tasks: [
    {
      name: { en: "Run a count", ar: "نفّذ جرداً" },
      steps: [
        { en: "Create a count for a warehouse.", ar: "أنشئ جرداً لمستودع." },
        { en: "Enter the counted quantity for each line.", ar: "أدخل الكمية المعدودة لكل سطر." },
        { en: "Post it — adjustments are made automatically.", ar: "رحّله — تُجرى التسويات تلقائياً." },
      ],
    },
  ],
  related: [
    { to: "/inventory/counts", label: { en: "All counts", ar: "كل عمليات الجرد" } },
    { to: "/inventory", label: { en: "Stock on hand", ar: "الأرصدة المتاحة" } },
  ],
};

export const stockCountDetailGuide: HelpGuide = {
  title: { en: "Count detail", ar: "تفاصيل الجرد" },
  purpose: {
    en: "Enter counted quantities for one stock count and post the result.",
    ar: "أدخل الكميات المعدودة لجرد واحد ورحّل النتيجة.",
  },
  howItWorks: {
    en: "Type the real shelf quantity against each line; the system shows the difference. Posting books the adjustments and locks the count.",
    ar: "اكتب الكمية الفعلية على الرفّ مقابل كل سطر؛ يعرض النظام الفرق. الترحيل يقيّد التسويات ويقفل الجرد.",
  },
  mistakes: [
    { en: "Double-check counts before posting — a posted count's adjustments are permanent ledger entries.", ar: "تحقّق مرتين قبل الترحيل — تسويات الجرد المُرحّل قيود دائمة في الدفتر." },
  ],
  related: [
    { to: "/inventory/counts", label: { en: "All counts", ar: "كل عمليات الجرد" } },
  ],
};

export const batchesGuide: HelpGuide = {
  title: { en: "Batches", ar: "التشغيلات" },
  purpose: {
    en: "Track received stock by batch/lot number and expiry date — useful for food, medicine, or anything that expires.",
    ar: "تابع المخزون المستلَم برقم تشغيلة وتاريخ صلاحية — مفيد للأغذية والأدوية وكل ما له صلاحية.",
  },
  howItWorks: {
    en: "When you receive stock you can tag a batch number and expiry. This report shows received quantity per batch and the earliest expiry, so you can use up older stock first.",
    ar: "عند الاستلام يمكنك وسم رقم تشغيلة وصلاحية. يعرض هذا التقرير الكمية المستلمة لكل تشغيلة وأقرب صلاحية، لتستهلك الأقدم أولاً.",
  },
  related: [
    { to: "/inventory/movements", label: { en: "Stock movement", ar: "حركة المخزون" } },
  ],
};
