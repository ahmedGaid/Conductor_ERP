import type { HelpGuide } from "../types";

export const ordersGuide: HelpGuide = {
  title: { en: "Sales orders", ar: "طلبات المبيعات" },
  purpose: {
    en: "Manage everything you sell to customers, from first order to final payment.",
    ar: "أدر كل ما تبيعه للعملاء، من أول طلب حتى آخر دفعة.",
  },
  howItWorks: {
    en: "An order moves through stages: draft → confirm → deliver → invoice → payment. Each stage does the right thing automatically — delivering reduces stock, invoicing records the receivable, payment clears it.",
    ar: "يمرّ الطلب بمراحل: مسودة ← تأكيد ← تسليم ← فوترة ← دفع. كل مرحلة تنفّذ الصحيح تلقائياً — التسليم يخفض المخزون، والفوترة تسجّل الذمة، والدفع يسوّيها.",
  },
  tasks: [
    {
      name: { en: "Create and process a sale", ar: "أنشئ بيعاً وعالجه" },
      steps: [
        { en: "Click 'New order', add the customer and lines.", ar: "انقر 'طلب جديد'، أضف العميل والسطور." },
        { en: "Confirm, then deliver, then invoice from the order's detail page.", ar: "أكّد، ثم سلّم، ثم افتر من صفحة تفاصيل الطلب." },
        { en: "Record the payment when the customer pays.", ar: "سجّل الدفعة عند دفع العميل." },
      ],
    },
  ],
  related: [
    { to: "/sales/orders/new", label: { en: "New order", ar: "طلب جديد" } },
    { to: "/sales/customers", label: { en: "Customers", ar: "العملاء" } },
    { to: "/sales/quotations", label: { en: "Quotations", ar: "عروض الأسعار" } },
  ],
};

export const newOrderGuide: HelpGuide = {
  title: { en: "New sales order", ar: "طلب مبيعات جديد" },
  purpose: {
    en: "Create a sales order: who's buying, what items, how many, and at what price.",
    ar: "أنشئ طلب مبيعات: من يشتري، وأي أصناف، وكم، وبأي سعر.",
  },
  howItWorks: {
    en: "Pick the customer and a warehouse, then add lines (item + quantity + price). The form totals the order live, including VAT if you choose a tax code and any line discounts.",
    ar: "اختر العميل ومخزناً، ثم أضف السطور (صنف + كمية + سعر). يجمع النموذج الطلب مباشرة، متضمناً الضريبة إن اخترت رمزاً ضريبياً وأي خصومات على السطور.",
  },
  sections: [
    {
      heading: { en: "Fields", ar: "الحقول" },
      items: [
        { term: { en: "Warehouse", ar: "المخزن" }, desc: { en: "Where the goods ship from — must have stock to deliver.", ar: "من أين تُشحن البضاعة — يجب أن يتوفر مخزون للتسليم." } },
        { term: { en: "Tax code", ar: "الرمز الضريبي" }, desc: { en: "Optional. Leave blank for no VAT; pick VAT14 to add 14%.", ar: "اختياري. اتركه فارغاً بلا ضريبة؛ اختر VAT14 لإضافة 14%." } },
        { term: { en: "Discount", ar: "الخصم" }, desc: { en: "Per-line amount off the gross.", ar: "مبلغ خصم لكل سطر من الإجمالي." } },
      ],
    },
  ],
  mistakes: [
    { en: "If a customer is over their credit limit, confirming the order will be blocked.", ar: "إذا تجاوز العميل حدّه الائتماني، يُمنع تأكيد الطلب." },
  ],
  related: [
    { to: "/sales", label: { en: "All orders", ar: "كل الطلبات" } },
  ],
};

export const orderDetailGuide: HelpGuide = {
  title: { en: "Order detail", ar: "تفاصيل الطلب" },
  purpose: {
    en: "Drive one order through its lifecycle and see its full history.",
    ar: "قُد طلباً واحداً عبر دورة حياته واطّلع على تاريخه الكامل.",
  },
  howItWorks: {
    en: "The action buttons change with the order's stage — confirm, deliver (full or partial), invoice, record payment, or process a return. Each action posts the matching stock/accounting effect.",
    ar: "تتغيّر أزرار الإجراءات مع مرحلة الطلب — تأكيد، تسليم (كامل أو جزئي)، فوترة، تسجيل دفعة، أو معالجة مرتجع. كل إجراء يرحّل الأثر المخزوني/المحاسبي المناسب.",
  },
  tasks: [
    {
      name: { en: "Handle a customer return", ar: "عالج مرتجع عميل" },
      steps: [
        { en: "Open the delivered/invoiced order.", ar: "افتح الطلب المُسلَّم/المفوتر." },
        { en: "Click Return and enter the quantities coming back.", ar: "انقر مرتجع وأدخل الكميات العائدة." },
        { en: "A credit note posts and the receivable drops.", ar: "يُرحّل إشعار دائن وتنخفض الذمة المدينة." },
      ],
    },
  ],
  related: [
    { to: "/sales", label: { en: "All orders", ar: "كل الطلبات" } },
  ],
};

export const invoiceDocumentGuide: HelpGuide = {
  title: { en: "Invoice document", ar: "مستند الفاتورة" },
  purpose: {
    en: "The clean, printable invoice your customer receives — ready to print or save as PDF.",
    ar: "الفاتورة النظيفة القابلة للطباعة التي يستلمها عميلك — جاهزة للطباعة أو الحفظ كـ PDF.",
  },
  howItWorks: {
    en: "It shows once an order is invoiced, with your company details, the customer, the lines, and the totals. Click Print and choose 'Save as PDF' to keep a copy — no extra tools needed.",
    ar: "تظهر بعد فوترة الطلب، وتعرض بيانات شركتك والعميل والسطور والمجاميع. انقر طباعة واختر 'حفظ كـ PDF' للاحتفاظ بنسخة — دون أي أدوات إضافية.",
  },
  mistakes: [
    { en: "Your company name and tax number come from Settings → Organization — fill them in so they appear here.", ar: "يأتي اسم شركتك ورقمك الضريبي من الإعدادات ← المؤسسة — أكملهما ليظهرا هنا." },
  ],
  related: [
    { to: "/settings/organization", label: { en: "Organization settings", ar: "إعدادات المؤسسة" } },
  ],
};

export const quotationsGuide: HelpGuide = {
  title: { en: "Quotations", ar: "عروض الأسعار" },
  purpose: {
    en: "Send customers a price quote before any sale is committed, then turn an accepted quote into an order in one click.",
    ar: "أرسل للعملاء عرض سعر قبل الالتزام بأي بيع، ثم حوّل العرض المقبول إلى طلب بنقرة واحدة.",
  },
  howItWorks: {
    en: "A quotation posts nothing to the books. It goes draft → submit → approve, and only when you Convert it does a real sales order get created. Larger quotes may need a manager's approval first.",
    ar: "عرض السعر لا يرحّل شيئاً للدفاتر. يمرّ بمسودة ← تقديم ← موافقة، وفقط عند التحويل يُنشأ طلب مبيعات حقيقي. قد تحتاج العروض الكبيرة موافقة مدير أولاً.",
  },
  tasks: [
    {
      name: { en: "Quote then convert", ar: "اعرض ثم حوّل" },
      steps: [
        { en: "Create a quotation and submit it.", ar: "أنشئ عرضاً وقدّمه." },
        { en: "Once approved, click Convert to make a sales order.", ar: "بعد الموافقة، انقر تحويل لإنشاء طلب مبيعات." },
      ],
    },
  ],
  related: [
    { to: "/sales/quotations/new", label: { en: "New quotation", ar: "عرض جديد" } },
    { to: "/sales", label: { en: "Sales orders", ar: "طلبات المبيعات" } },
  ],
};

export const newQuotationGuide: HelpGuide = {
  title: { en: "New quotation", ar: "عرض سعر جديد" },
  purpose: {
    en: "Draft a price quote for a customer without affecting stock or the books.",
    ar: "حرّر عرض سعر لعميل دون التأثير على المخزون أو الدفاتر.",
  },
  howItWorks: {
    en: "Add the customer and lines just like an order; the totals preview what the eventual sale would be. Submit it to start the approval/convert flow.",
    ar: "أضف العميل والسطور كما في الطلب؛ تعرض المجاميع كيف سيكون البيع المحتمل. قدّمه لبدء مسار الموافقة/التحويل.",
  },
  related: [
    { to: "/sales/quotations", label: { en: "All quotations", ar: "كل العروض" } },
  ],
};

export const quotationDetailGuide: HelpGuide = {
  title: { en: "Quotation detail", ar: "تفاصيل العرض" },
  purpose: {
    en: "Move one quotation through submit, approve/reject, and convert.",
    ar: "حرّك عرضاً واحداً عبر التقديم والموافقة/الرفض والتحويل.",
  },
  howItWorks: {
    en: "Convert is only available after approval, and each quote can be converted once. The resulting order number is shown so you can open it.",
    ar: "التحويل متاح فقط بعد الموافقة، ويمكن تحويل كل عرض مرة واحدة. يُعرض رقم الطلب الناتج لتفتحه.",
  },
  related: [
    { to: "/sales/quotations", label: { en: "All quotations", ar: "كل العروض" } },
  ],
};

export const customersGuide: HelpGuide = {
  title: { en: "Customers", ar: "العملاء" },
  purpose: {
    en: "Your customer directory — names, contact details, and credit limits.",
    ar: "دليل عملائك — الأسماء وبيانات الاتصال والحدود الائتمانية.",
  },
  howItWorks: {
    en: "A customer's credit limit caps how much they can owe at once; the system blocks confirming an order that would exceed it. Set customers up here before selling to them.",
    ar: "يحدّ الحدّ الائتماني للعميل أقصى ما يمكن أن يدين به دفعة واحدة؛ ويمنع النظام تأكيد طلب يتجاوزه. هيّئ العملاء هنا قبل البيع لهم.",
  },
  related: [
    { to: "/sales", label: { en: "Sales orders", ar: "طلبات المبيعات" } },
  ],
};

export const customerDetailGuide: HelpGuide = {
  title: { en: "Customer", ar: "العميل" },
  purpose: {
    en: "View and edit a customer's details and see their order history.",
    ar: "اعرض بيانات العميل وعدّلها وتابع سجل طلباتهم.",
  },
  howItWorks: {
    en: "Edit the customer's name, code, or contact details directly on this page.",
    ar: "عدّل اسم العميل أو كوده أو بيانات التواصل مباشرة من هذه الصفحة.",
  },
  related: [
    { to: "/sales/customers", label: { en: "All customers", ar: "جميع العملاء" } },
  ],
};
