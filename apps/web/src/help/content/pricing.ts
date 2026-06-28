import type { HelpGuide } from "../types";

export const priceListsGuide: HelpGuide = {
  title: { en: "Pricing", ar: "التسعير" },
  purpose: {
    en: "Price lists hold what you charge for each item. A new order or quotation fills in a line's price automatically from these.",
    ar: "تحفظ قوائم الأسعار ما تتقاضاه عن كل صنف. يملأ الطلب أو عرض السعر الجديد سعر السطر تلقائيًا من هذه القوائم.",
  },
  howItWorks: {
    en: "Keep one list marked Default — it applies to any customer you haven't assigned a specific list. Mark a list 'tax-inclusive' if its prices already include VAT; the system backs the tax out when it fills an order line. A customer's own list, or a negotiated price for one item, always wins over the default.",
    ar: "احتفظ بقائمة واحدة معلَّمة كافتراضية — تنطبق على أي عميل لم تُسنِد له قائمة بعينها. علِّم القائمة «شاملة الضريبة» إذا كانت أسعارها تتضمن ضريبة القيمة المضافة؛ ويستخرج النظام الضريبة عند ملء سطر الطلب. قائمة العميل الخاصة، أو سعر متفاوَض عليه لصنف واحد، تَغلِب الافتراضية دائمًا.",
  },
  related: [
    { to: "/sales/orders/new", label: { en: "New order", ar: "طلب جديد" } },
    { to: "/inventory/items", label: { en: "Items", ar: "الأصناف" } },
  ],
};

export const customerPricingGuide: HelpGuide = {
  title: { en: "Customer pricing", ar: "تسعير العملاء" },
  purpose: {
    en: "Decide which list a customer is charged from, and set negotiated prices for single items — both fill in automatically on that customer's next order.",
    ar: "حدِّد القائمة التي يُحاسَب منها العميل، واضبط أسعارًا متفاوَضًا عليها لأصناف بعينها — وكلاهما يُملأ تلقائيًا في طلب العميل التالي.",
  },
  howItWorks: {
    en: "Assign a customer to a price list and that list replaces the default for them. An item override goes further: one price for one item for one customer, optionally only at or above a quantity, only inside a date range, and tax-inclusive if you mark it. An override always wins over the assigned list, which wins over the default.",
    ar: "أسنِد العميل إلى قائمة أسعار فتحلّ تلك القائمة محل الافتراضية له. سعر الصنف الخاص يذهب أبعد: سعر واحد لصنف واحد لعميل واحد، ويمكن قصره على كمية معينة فأكثر، أو على مدى تواريخ، وشاملًا الضريبة إن علَّمته. السعر الخاص يَغلِب القائمة المُسنَدة، وهي تَغلِب الافتراضية.",
  },
  related: [
    { to: "/pricing", label: { en: "All price lists", ar: "كل قوائم الأسعار" } },
    { to: "/sales/customers", label: { en: "Customers", ar: "العملاء" } },
  ],
};

export const priceListDetailGuide: HelpGuide = {
  title: { en: "Price list", ar: "قائمة الأسعار" },
  purpose: {
    en: "The prices on one list — one row per item, with an optional quantity break so a larger order can earn a lower price.",
    ar: "أسعار قائمة واحدة — سطر لكل صنف، مع كسر كمية اختياري بحيث يحصل الطلب الأكبر على سعر أقل.",
  },
  howItWorks: {
    en: "Add an item and its unit price. Set 'from quantity' to make a price apply only at or above that amount — leave it 0 for the everyday price. The toggles at the top set whether this is the default list, whether its prices include tax, and whether it's active.",
    ar: "أضف صنفًا وسعر وحدته. اضبط «ابتداءً من كمية» ليطبَّق السعر عند تلك الكمية أو أكثر فقط — اتركها 0 للسعر المعتاد. تحدّد المفاتيح في الأعلى ما إذا كانت هذه القائمة الافتراضية، وهل أسعارها شاملة الضريبة، وهل هي نشطة.",
  },
  related: [
    { to: "/pricing", label: { en: "All price lists", ar: "كل قوائم الأسعار" } },
  ],
};
