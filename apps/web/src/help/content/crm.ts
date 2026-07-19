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
  checklist: {
    name: { en: "Add your first opportunity", ar: "أضف أول فرصة" },
    doneMessage: {
      en: "Opportunity added — it starts in Qualifying. Advance its stage as the deal moves forward.",
      ar: "أُضيفت الفرصة — تبدأ في «تأهيل». قدّم مرحلتها مع تقدّم الصفقة.",
    },
    steps: [
      {
        label: { en: "Enter a name and pick the customer", ar: "أدخل اسماً واختر العميل" },
        detail: [
          { en: "The name is your own label for the deal; the customer is who you're selling to.", ar: "الاسم تسمية خاصة بك للصفقة؛ العميل هو من تبيع له." },
        ],
        hint: { en: "Name and customer set. Add at least one line to see the value.", ar: "تم تحديد الاسم والعميل. أضف سطراً واحداً على الأقل لرؤية القيمة." },
        done: (s) => (s.nameSet === true && s.customerPicked === true) || (s.opportunityCount as number) > 0,
      },
      {
        label: { en: "Click Create opportunity", ar: "اضغط «إنشاء فرصة»" },
        detail: [
          { en: "It appears in Qualifying — switch to Board view to see it move across stages.", ar: "تظهر في «تأهيل» — بدّل إلى عرض «لوحة» لرؤيتها تتنقل بين المراحل." },
        ],
        done: (s) => (s.opportunityCount as number) > 0,
      },
    ],
  },
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
  checklist: {
    name: { en: "Add your first lead", ar: "أضف أول عميل محتمل" },
    doneMessage: {
      en: "Lead added — it now shows in the list with status New. Qualify it once you've assessed it.",
      ar: "تمت إضافة العميل المحتمل — يظهر الآن في القائمة بحالة «جديد». أهّله بعد تقييمه.",
    },
    steps: [
      {
        label: { en: "Enter the lead's name", ar: "أدخل اسم العميل المحتمل" },
        detail: [
          {
            en: "Type a name in the Name field of the add-lead row above the list.",
            ar: "اكتب اسماً في حقل الاسم بصف الإضافة أعلى القائمة.",
          },
          {
            en: "Company, email, and source are optional — fill in what you know, leave the rest.",
            ar: "الشركة والبريد والمصدر اختيارية — املأ ما تعرفه واترك الباقي.",
          },
        ],
        hint: { en: "Name set. Now add it.", ar: "تم إدخال الاسم. الآن أضفه." },
        done: (s) => (s.leadCount as number) > 0,
      },
      {
        label: { en: "Click Add lead", ar: "اضغط «إضافة»" },
        detail: [
          { en: "It appears at the top of the list instantly, with status New.", ar: "يظهر أعلى القائمة فوراً بحالة «جديد»." },
        ],
        done: (s) => (s.leadCount as number) > 0,
      },
    ],
  },
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
  checklist: {
    name: { en: "Log your first ticket", ar: "سجّل أول تذكرة" },
    doneMessage: {
      en: "Ticket logged — its SLA clock starts now. Track it from this list until it's resolved.",
      ar: "سُجّلت التذكرة — بدأ عدّاد مستوى الخدمة الآن. تابعها من هذه القائمة حتى حلّها.",
    },
    steps: [
      {
        label: { en: "Enter the subject", ar: "أدخل الموضوع" },
        detail: [
          { en: "A short line describing the issue — this is what shows in the list.", ar: "سطر قصير يصف المشكلة — هذا ما يظهر في القائمة." },
        ],
        hint: { en: "Subject set. Now link it to a customer.", ar: "تم إدخال الموضوع. الآن اربطه بعميل." },
        done: (s) => s.subjectSet === true || (s.ticketCount as number) > 0,
      },
      {
        label: { en: "Pick the customer", ar: "اختر العميل" },
        detail: [
          { en: "Search by name in the Customer field.", ar: "ابحث بالاسم في حقل العميل." },
        ],
        hint: { en: "Customer set. Priority defaults to Medium — raise it now if this is urgent.", ar: "تم تحديد العميل. الأولوية الافتراضية متوسطة — ارفعها الآن إن كانت عاجلة." },
        done: (s) => s.customerPicked === true || (s.ticketCount as number) > 0,
      },
      {
        label: { en: "Click Add", ar: "اضغط «إضافة»" },
        done: (s) => (s.ticketCount as number) > 0,
      },
    ],
  },
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
  checklist: {
    name: { en: "Add your first campaign", ar: "أضف أول حملة" },
    doneMessage: {
      en: "Campaign added. Tag leads and opportunities with it to start measuring ROI.",
      ar: "أُضيفت الحملة. سِم بها العملاء المحتملين والفرص لتبدأ قياس العائد.",
    },
    steps: [
      {
        label: { en: "Enter a code and name", ar: "أدخل رمزاً واسماً" },
        detail: [
          { en: "The code is a short reference; the name is what shows in reports.", ar: "الرمز مرجع قصير؛ الاسم هو ما يظهر في التقارير." },
        ],
        hint: { en: "Code and name set. Cost is optional — add it to see ROI later.", ar: "تم إدخال الرمز والاسم. التكلفة اختيارية — أضفها لرؤية العائد لاحقاً." },
        done: (s) => (s.campaignCount as number) > 0,
      },
      {
        label: { en: "Click Add campaign", ar: "اضغط «إضافة حملة»" },
        done: (s) => (s.campaignCount as number) > 0,
      },
    ],
  },
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
