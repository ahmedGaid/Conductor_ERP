import type { HelpGuide } from "../types";

export const purchaseOrdersGuide: HelpGuide = {
  title: { en: "Purchase orders", ar: "أوامر الشراء" },
  purpose: {
    en: "Manage everything you buy from suppliers, from ordering to paying the bill.",
    ar: "أدر كل ما تشتريه من الموردين، من الطلب حتى سداد الفاتورة.",
  },
  howItWorks: {
    en: "A purchase order moves: draft → confirm → receive → bill → payment. Receiving raises stock; billing runs a three-way match (you can only bill what you received) and records what you owe; payment clears it.",
    ar: "يمرّ أمر الشراء: مسودة ← تأكيد ← استلام ← فوترة ← دفع. الاستلام يزيد المخزون؛ والفوترة تجري مطابقة ثلاثية (تفوتر فقط ما استلمته) وتسجّل ما عليك؛ والدفع يسوّيه.",
  },
  tasks: [
    {
      name: { en: "Order and receive goods", ar: "اطلب واستلم بضاعة" },
      steps: [
        { en: "Create a PO with the supplier and lines, then confirm.", ar: "أنشئ أمر شراء بالمورد والسطور ثم أكّد." },
        { en: "Receive the goods (full or partial) when they arrive.", ar: "استلم البضاعة (كامل أو جزئي) عند وصولها." },
        { en: "Bill it against the supplier invoice, then pay.", ar: "افتر مقابل فاتورة المورد ثم ادفع." },
      ],
    },
  ],
  related: [
    { to: "/purchasing/orders/new", label: { en: "New purchase order", ar: "أمر شراء جديد" } },
    { to: "/purchasing/suppliers", label: { en: "Suppliers", ar: "الموردون" } },
    { to: "/purchasing/requests", label: { en: "Purchase requests", ar: "طلبات الشراء" } },
  ],
};

export const newPurchaseOrderGuide: HelpGuide = {
  title: { en: "New purchase order", ar: "أمر شراء جديد" },
  purpose: {
    en: "Order goods or materials from a supplier.",
    ar: "اطلب بضاعة أو مواد من مورد.",
  },
  howItWorks: {
    en: "Pick the supplier and destination warehouse, then add lines (item + quantity + cost). Choose a tax code if the purchase carries recoverable VAT.",
    ar: "اختر المورد ومخزن الوجهة، ثم أضف السطور (صنف + كمية + تكلفة). اختر رمزاً ضريبياً إن كانت المشتريات تحمل ضريبة قابلة للاسترداد.",
  },
  related: [
    { to: "/purchasing", label: { en: "All purchase orders", ar: "كل أوامر الشراء" } },
  ],
};

export const purchaseOrderDetailGuide: HelpGuide = {
  title: { en: "Purchase order detail", ar: "تفاصيل أمر الشراء" },
  purpose: {
    en: "Drive one purchase order through receiving, billing, payment, and returns.",
    ar: "قُد أمر شراء واحداً عبر الاستلام والفوترة والدفع والمرتجعات.",
  },
  howItWorks: {
    en: "Action buttons follow the stage. The three-way match means a bill is blocked until received quantities match the order, protecting you from paying for goods you didn't get.",
    ar: "تتبع أزرار الإجراءات المرحلة. المطابقة الثلاثية تعني منع الفوترة حتى تطابق الكميات المستلمة الطلب، لتحميك من دفع ثمن بضاعة لم تستلمها.",
  },
  tasks: [
    {
      name: { en: "Return goods to a supplier", ar: "أرجع بضاعة لمورد" },
      steps: [
        { en: "Open the received PO and click Return.", ar: "افتح أمر الشراء المستلَم وانقر مرتجع." },
        { en: "Enter the quantities going back; a debit note posts.", ar: "أدخل الكميات العائدة؛ يُرحّل إشعار مدين." },
      ],
    },
  ],
  related: [
    { to: "/purchasing", label: { en: "All purchase orders", ar: "كل أوامر الشراء" } },
  ],
};

export const purchaseRequestsGuide: HelpGuide = {
  title: { en: "Purchase requests", ar: "طلبات الشراء" },
  purpose: {
    en: "Let staff request a purchase and get it approved before any order is placed with a supplier.",
    ar: "دع الموظفين يطلبون شراءً ويحصلون على موافقة قبل وضع أي أمر لدى مورد.",
  },
  howItWorks: {
    en: "A request posts nothing. It goes draft → submit → approve, and converting an approved request creates a real purchase order. Larger requests need a manager's approval.",
    ar: "الطلب لا يرحّل شيئاً. يمرّ بمسودة ← تقديم ← موافقة، وتحويل الطلب المعتمد يُنشئ أمر شراء حقيقياً. الطلبات الكبيرة تحتاج موافقة مدير.",
  },
  related: [
    { to: "/purchasing/requests/new", label: { en: "New request", ar: "طلب جديد" } },
    { to: "/purchasing", label: { en: "Purchase orders", ar: "أوامر الشراء" } },
  ],
};

export const newPurchaseRequestGuide: HelpGuide = {
  title: { en: "New purchase request", ar: "طلب شراء جديد" },
  purpose: {
    en: "Ask for goods to be bought, for approval before ordering.",
    ar: "اطلب شراء بضاعة، للموافقة قبل الطلب.",
  },
  howItWorks: {
    en: "Add the items and quantities you need. Submit it to start the approval flow; once approved it can be converted to a purchase order.",
    ar: "أضف الأصناف والكميات التي تحتاجها. قدّمه لبدء مسار الموافقة؛ وبعد الاعتماد يمكن تحويله إلى أمر شراء.",
  },
  related: [
    { to: "/purchasing/requests", label: { en: "All requests", ar: "كل الطلبات" } },
  ],
};

export const purchaseRequestDetailGuide: HelpGuide = {
  title: { en: "Purchase request detail", ar: "تفاصيل طلب الشراء" },
  purpose: {
    en: "Move one request through submit, approve/reject, and convert to a PO.",
    ar: "حرّك طلباً واحداً عبر التقديم والموافقة/الرفض والتحويل إلى أمر شراء.",
  },
  howItWorks: {
    en: "Convert is available only after approval and works once per request; the new PO number is shown.",
    ar: "التحويل متاح فقط بعد الموافقة ويعمل مرة لكل طلب؛ ويُعرض رقم أمر الشراء الجديد.",
  },
  related: [
    { to: "/purchasing/requests", label: { en: "All requests", ar: "كل الطلبات" } },
  ],
};

export const suppliersGuide: HelpGuide = {
  title: { en: "Suppliers", ar: "الموردون" },
  purpose: {
    en: "Your supplier directory — who you buy from and how to reach them.",
    ar: "دليل مورّديك — ممّن تشتري وكيف تصل إليهم.",
  },
  howItWorks: {
    en: "Set up suppliers here so you can select them on purchase orders and track what you owe each one.",
    ar: "هيّئ الموردين هنا لتختارهم في أوامر الشراء وتتابع ما عليك لكل منهم.",
  },
  related: [
    { to: "/purchasing", label: { en: "Purchase orders", ar: "أوامر الشراء" } },
  ],
};

export const supplierDetailGuide: HelpGuide = {
  title: { en: "Supplier", ar: "المورّد" },
  purpose: {
    en: "View and edit a supplier's details and see their order history.",
    ar: "اعرض بيانات المورّد وعدّلها وتابع سجل طلباتهم.",
  },
  howItWorks: {
    en: "Edit the supplier's name, code, or contact details directly on this page.",
    ar: "عدّل اسم المورّد أو كوده أو بيانات التواصل مباشرة من هذه الصفحة.",
  },
  related: [
    { to: "/purchasing/suppliers", label: { en: "All suppliers", ar: "جميع الموردين" } },
  ],
};
