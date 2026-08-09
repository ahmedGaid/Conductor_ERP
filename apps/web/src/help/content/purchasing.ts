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
  alerts: [
    {
      when: (s) => s.hasError === true,
      tone: "warn",
      title: { en: "Something needs fixing", ar: "هناك ما يحتاج تصحيحاً" },
      body: {
        en: "The red message above the button explains what's missing — fix that, then submit again.",
        ar: "الرسالة الحمراء فوق الزر توضّح الناقص — صحّحها ثم أرسل مرة أخرى.",
      },
    },
  ],
  checklist: {
    name: { en: "Build this purchase order", ar: "أنشئ أمر الشراء هذا" },
    doneMessage: {
      en: "Everything's filled in — review the total, then click Create order.",
      ar: "كل شيء مكتمل — راجع الإجمالي ثم اضغط «إنشاء الطلب».",
    },
    steps: [
      {
        label: { en: "Pick the supplier", ar: "اختر المورد" },
        detail: [
          {
            en: "Open the Supplier field and search by name — start typing and the list narrows.",
            ar: "افتح حقل المورد وابحث بالاسم — ابدأ الكتابة وتضيق القائمة.",
          },
        ],
        hint: { en: "Supplier set. Now pick the destination.", ar: "تم تحديد المورد. الآن اختر الوجهة." },
        done: (s) => s.supplierPicked === true,
      },
      {
        label: { en: "Pick the destination warehouse", ar: "اختر مخزن الوجهة" },
        detail: [
          {
            en: "Open the Warehouse field — pick the one the goods will arrive at.",
            ar: "افتح حقل المخزن — اختر الذي ستصل إليه البضاعة.",
          },
        ],
        hint: { en: "Warehouse set. Now add what you're ordering.", ar: "تم تحديد المخزن. الآن أضف ما تطلبه." },
        done: (s) => s.warehousePicked === true,
      },
      {
        label: { en: "Add at least one item line", ar: "أضف سطر صنف واحد على الأقل" },
        detail: [
          {
            en: "In the item row, search and pick a product.",
            ar: "في سطر الصنف، ابحث واختر منتجاً.",
          },
          {
            en: "Set the quantity and the cost you're paying per unit.",
            ar: "حدّد الكمية والتكلفة التي تدفعها لكل وحدة.",
          },
          {
            en: "Click Add line for a second item, or leave it at one.",
            ar: "اضغط «إضافة سطر» لصنف ثانٍ، أو اتركه بصنف واحد.",
          },
        ],
        done: (s) => s.lineReady === true,
      },
    ],
  },
  related: [
    { to: "/purchasing", label: { en: "All purchase orders", ar: "كل أوامر الشراء" } },
  ],
};

export const editPurchaseOrderGuide: HelpGuide = {
  title: { en: "Edit purchase order", ar: "تعديل أمر الشراء" },
  purpose: {
    en: "Change the supplier, warehouse, or lines on an order that hasn't been confirmed yet.",
    ar: "غيّر المورّد أو المخزن أو السطور في أمر لم يُؤكَّد بعد.",
  },
  howItWorks: {
    en: "Only draft orders can be edited — once an order is confirmed this page won't open. Your changes autosave as you type; if you leave and come back, a banner offers to continue where you left off.",
    ar: "لا يمكن تعديل إلا الأوامر في حالة مسودة — بمجرد تأكيد الأمر لن تفتح هذه الصفحة. تُحفظ تغييراتك تلقائياً أثناء الكتابة؛ وإن غادرت وعدت، يعرض شريط متابعة العمل من حيث توقفت.",
  },
  related: [
    { to: "/purchasing/orders/:id", label: { en: "Purchase order detail", ar: "تفاصيل أمر الشراء" } },
    { to: "/drafts", label: { en: "Unfinished work", ar: "العمل غير المكتمل" } },
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

export const importInvoiceGuide: HelpGuide = {
  title: { en: "Import invoice", ar: "استيراد فاتورة" },
  purpose: {
    en: "Turn a photo or PDF of a supplier invoice into a draft purchase order — the assistant reads it, you review and decide.",
    ar: "حوّل صورة أو PDF لفاتورة مورد إلى مسودة أمر شراء — المساعد الذكي يقرأها، وأنت تراجع وتقرر.",
  },
  howItWorks: {
    en: "Upload the document. The assistant extracts the supplier, lines, and totals, and matches them to your records. Everything is editable; nothing posts until you create the draft, which then follows the normal confirm → receive → bill path.",
    ar: "ارفع المستند. يستخرج المساعد الذكي المورد والبنود والإجماليات ويطابقها بسجلاتك. كل شيء قابل للتعديل؛ ولا يُرحَّل شيء حتى تنشئ المسودة، ثم تتبع المسار المعتاد: تأكيد ← استلام ← فوترة.",
  },
  tasks: [
    {
      name: { en: "From photo to draft PO", ar: "من صورة إلى مسودة أمر شراء" },
      steps: [
        { en: "Photograph the invoice or pick a PDF (up to 5 MB).", ar: "صوّر الفاتورة أو اختر ملف PDF (حتى 5 ميجابايت)." },
        { en: "Check the matched supplier and lines; fix anything the assistant flagged.", ar: "تحقق من المورد والبنود المطابقة؛ وصحّح ما أشار إليه المساعد الذكي." },
        { en: "Create the draft — it opens as a normal purchase order.", ar: "أنشئ المسودة — تُفتح كأمر شراء عادي." },
      ],
    },
  ],
  related: [
    { to: "/purchasing", label: { en: "Purchase orders", ar: "أوامر الشراء" } },
    { to: "/purchasing/suppliers", label: { en: "Suppliers", ar: "الموردون" } },
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
  alerts: [
    {
      when: (s) => s.hasError === true,
      tone: "warn",
      title: { en: "Can't submit yet", ar: "لا يمكن التقديم بعد" },
      body: { en: "Check the message below the form — usually a missing supplier, warehouse, or line.", ar: "راجع الرسالة أسفل النموذج — عادة مورّد أو مخزن أو سطر ناقص." },
    },
  ],
  checklist: {
    name: { en: "Submit your first request", ar: "قدّم أول طلب" },
    doneMessage: {
      en: "Request submitted — it's now waiting for approval. Once approved, convert it to a purchase order.",
      ar: "قُدّم الطلب — وهو الآن ينتظر الموافقة. بعد الاعتماد حوّله إلى أمر شراء.",
    },
    steps: [
      {
        label: { en: "Pick the supplier", ar: "اختر المورّد" },
        detail: [
          { en: "Search by code or name in the Supplier field.", ar: "ابحث بالكود أو الاسم في حقل المورّد." },
        ],
        hint: { en: "Supplier set. Now pick the warehouse it should arrive at.", ar: "تم تحديد المورّد. الآن اختر المخزن الذي سيصل إليه." },
        done: (s) => s.supplierPicked === true,
      },
      {
        label: { en: "Pick the warehouse", ar: "اختر المخزن" },
        detail: [
          { en: "This is where the goods will be received once the request becomes an order.", ar: "هنا تُستلم البضاعة بعد أن يصبح الطلب أمر شراء." },
        ],
        hint: { en: "Warehouse set. Now add at least one item.", ar: "تم تحديد المخزن. الآن أضف صنفاً واحداً على الأقل." },
        done: (s) => s.warehousePicked === true,
      },
      {
        label: { en: "Add a line: item, quantity, cost", ar: "أضف سطراً: صنف وكمية وتكلفة" },
        detail: [
          { en: "Pick the item, type the quantity, and type the expected unit cost.", ar: "اختر الصنف واكتب الكمية واكتب التكلفة المتوقعة للوحدة." },
        ],
        hint: { en: "Line ready. Click Submit request.", ar: "السطر جاهز. اضغط «تقديم الطلب»." },
        done: (s) => s.lineReady === true,
      },
      {
        label: { en: "Click Submit request", ar: "اضغط «تقديم الطلب»" },
        done: (s) => s.lineReady === true && s.supplierPicked === true && s.warehousePicked === true,
      },
    ],
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
  checklist: {
    name: { en: "Add your first supplier", ar: "أضف أول مورّد" },
    doneMessage: {
      en: "Supplier added — pick them on any new purchase order or request.",
      ar: "أُضيف المورّد — اختره في أي أمر شراء أو طلب جديد.",
    },
    steps: [
      {
        label: { en: "Enter a code", ar: "أدخل كوداً" },
        detail: [
          { en: "A short unique code you'll recognize in lists — letters/numbers, e.g. SUP-001.", ar: "كود قصير مميّز تتعرف عليه في القوائم — حروف/أرقام، مثل SUP-001." },
        ],
        hint: { en: "Code set. Now enter the name.", ar: "تم إدخال الكود. الآن أدخل الاسم." },
        done: (s) => s.codeSet === true || (s.supplierCount as number) > 0,
      },
      {
        label: { en: "Enter the name", ar: "أدخل الاسم" },
        hint: { en: "Name set. Click Add.", ar: "تم إدخال الاسم. اضغط «إضافة»." },
        done: (s) => s.nameSet === true || (s.supplierCount as number) > 0,
      },
      {
        label: { en: "Click Add", ar: "اضغط «إضافة»" },
        done: (s) => (s.supplierCount as number) > 0,
      },
    ],
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
