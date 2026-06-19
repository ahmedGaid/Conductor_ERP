import type { HelpGuide } from "../types";

export const pipelineGuide: HelpGuide = {
  title: { en: "Sales pipeline", ar: "خط المبيعات" },
  purpose: {
    en: "Track your sales opportunities (deals) as they move from first interest toward winning or losing.",
    ar: "تابع فرص المبيعات (الصفقات) وهي تتحرك من أول اهتمام نحو الكسب أو الخسارة.",
  },
  howItWorks: {
    en: "Each deal sits in a stage: qualifying → proposal → negotiation → won or lost. When you mark a deal 'won', the system hands it to Sales and creates a draft sales order automatically — no re-typing.",
    ar: "تقع كل صفقة في مرحلة: تأهيل ← عرض ← تفاوض ← مكسوبة أو مخسورة. وعند تعليم صفقة 'مكسوبة'، يسلّمها النظام للمبيعات وينشئ طلب مبيعات مسودة تلقائياً — دون إعادة كتابة.",
  },
  tasks: [
    {
      name: { en: "Win a deal", ar: "اكسب صفقة" },
      steps: [
        { en: "Open the opportunity and advance its stage.", ar: "افتح الفرصة وقدّم مرحلتها." },
        { en: "Mark it Won — a draft sales order is created for you.", ar: "علّمها مكسوبة — يُنشأ لك طلب مبيعات مسودة." },
      ],
    },
  ],
  related: [
    { to: "/crm/leads", label: { en: "Leads", ar: "العملاء المحتملون" } },
    { to: "/sales", label: { en: "Sales orders", ar: "طلبات المبيعات" } },
  ],
};

export const opportunityDetailGuide: HelpGuide = {
  title: { en: "Opportunity detail", ar: "تفاصيل الفرصة" },
  purpose: {
    en: "Manage one deal: its value, stage, line items, and the outcome.",
    ar: "أدر صفقة واحدة: قيمتها ومرحلتها وبنودها ونتيجتها.",
  },
  howItWorks: {
    en: "Advance the stage as the deal progresses. Winning needs a known customer and at least one line, because it becomes a real sales order; losing simply closes the deal.",
    ar: "قدّم المرحلة مع تقدّم الصفقة. الكسب يحتاج عميلاً معروفاً وسطراً واحداً على الأقل لأنه يصبح طلب مبيعات حقيقياً؛ والخسارة تغلق الصفقة فقط.",
  },
  related: [
    { to: "/crm/pipeline", label: { en: "Pipeline", ar: "خط المبيعات" } },
  ],
};

export const leadsGuide: HelpGuide = {
  title: { en: "Leads", ar: "العملاء المحتملون" },
  purpose: {
    en: "Capture potential customers before they become real deals.",
    ar: "التقط العملاء المحتملين قبل أن يصبحوا صفقات حقيقية.",
  },
  howItWorks: {
    en: "Record a lead, qualify it, then convert it once into an opportunity in the pipeline. A lead can only be converted a single time.",
    ar: "سجّل عميلاً محتملاً، أهّله، ثم حوّله مرة واحدة إلى فرصة في خط المبيعات. لا يمكن تحويل العميل المحتمل إلا مرة واحدة.",
  },
  tasks: [
    {
      name: { en: "Turn a lead into a deal", ar: "حوّل محتملاً إلى صفقة" },
      steps: [
        { en: "Qualify the lead once you've assessed it.", ar: "أهّل المحتمل بعد تقييمه." },
        { en: "Convert it — it appears in the pipeline as an opportunity.", ar: "حوّله — يظهر في خط المبيعات كفرصة." },
      ],
    },
  ],
  related: [
    { to: "/crm/pipeline", label: { en: "Pipeline", ar: "خط المبيعات" } },
    { to: "/crm/campaigns", label: { en: "Campaigns", ar: "الحملات" } },
  ],
};

export const ticketsGuide: HelpGuide = {
  title: { en: "Support tickets", ar: "تذاكر الدعم" },
  purpose: {
    en: "Track customer support requests and make sure none are left too long.",
    ar: "تابع طلبات دعم العملاء وتأكّد ألا يُترك أي منها طويلاً.",
  },
  howItWorks: {
    en: "Each ticket has a priority that sets a response deadline (its SLA). If it passes the deadline while still open, it's 'breached' and can be escalated — bumping its priority and alerting the team (a WhatsApp notification is sent).",
    ar: "لكل تذكرة أولوية تحدّد موعد استجابة (مستوى الخدمة). وإن تجاوزت الموعد وهي مفتوحة، تصبح 'متجاوزة' ويمكن تصعيدها — برفع أولويتها وتنبيه الفريق (يُرسل إشعار واتساب).",
  },
  sections: [
    {
      heading: { en: "Priority & SLA", ar: "الأولوية ومستوى الخدمة" },
      items: [
        { term: { en: "Urgent / High / Medium / Low", ar: "عاجل / مرتفع / متوسط / منخفض" }, desc: { en: "Higher priority = shorter deadline to respond.", ar: "أولوية أعلى = موعد استجابة أقصر." } },
        { term: { en: "Breached", ar: "متجاوزة" }, desc: { en: "Still open past its deadline — escalate it.", ar: "ما زالت مفتوحة بعد موعدها — صعّدها." } },
      ],
    },
  ],
  tasks: [
    {
      name: { en: "Escalate a breached ticket", ar: "صعّد تذكرة متجاوزة" },
      steps: [
        { en: "Find a ticket marked breached.", ar: "جد تذكرة معلّمة كمتجاوزة." },
        { en: "Click Escalate (or 'Run escalations' to sweep all of them).", ar: "انقر تصعيد (أو 'تشغيل التصعيدات' لمعالجتها جميعاً)." },
      ],
    },
  ],
  tips: [
    { en: "Each breach escalates only once, so running escalations repeatedly is safe.", ar: "كل تجاوز يُصعّد مرة واحدة فقط، لذا تكرار تشغيل التصعيدات آمن." },
  ],
  related: [
    { to: "/notifications", label: { en: "Notifications", ar: "الإشعارات" } },
  ],
};

export const campaignsGuide: HelpGuide = {
  title: { en: "Campaigns", ar: "الحملات" },
  purpose: {
    en: "Group marketing efforts and measure their return — did the money spent bring in deals?",
    ar: "اجمع الجهود التسويقية وقِس عائدها — هل جلب المال المنفَق صفقات؟",
  },
  howItWorks: {
    en: "Create a campaign with its cost, then link leads and opportunities to it. The campaign shows its ROI: the value of deals won against what you spent.",
    ar: "أنشئ حملة بتكلفتها، ثم اربط بها العملاء المحتملين والفرص. تعرض الحملة عائدها: قيمة الصفقات المكسوبة مقابل ما أنفقته.",
  },
  tasks: [
    {
      name: { en: "Measure a campaign", ar: "قِس حملة" },
      steps: [
        { en: "Create the campaign with its budget/cost.", ar: "أنشئ الحملة بميزانيتها/تكلفتها." },
        { en: "Tag leads and opportunities with the campaign.", ar: "وسِم العملاء المحتملين والفرص بالحملة." },
        { en: "Open it to read won value, pipeline, and ROI.", ar: "افتحها لقراءة القيمة المكسوبة وخط المبيعات والعائد." },
      ],
    },
  ],
  related: [
    { to: "/crm/leads", label: { en: "Leads", ar: "العملاء المحتملون" } },
    { to: "/crm/pipeline", label: { en: "Pipeline", ar: "خط المبيعات" } },
  ],
};

export const campaignDetailGuide: HelpGuide = {
  title: { en: "Campaign detail", ar: "تفاصيل الحملة" },
  purpose: {
    en: "See one campaign's performance and manage its status.",
    ar: "اطّلع على أداء حملة واحدة وأدر حالتها.",
  },
  howItWorks: {
    en: "The metrics roll up the linked deals: won value, open pipeline, counts, and ROI versus the campaign cost. Activate or complete the campaign from here.",
    ar: "تجمع المؤشرات الصفقات المرتبطة: القيمة المكسوبة، خط المبيعات المفتوح، الأعداد، والعائد مقابل تكلفة الحملة. فعّل الحملة أو أكملها من هنا.",
  },
  related: [
    { to: "/crm/campaigns", label: { en: "All campaigns", ar: "كل الحملات" } },
  ],
};
