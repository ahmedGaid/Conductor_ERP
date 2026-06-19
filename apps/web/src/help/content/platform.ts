import type { HelpGuide } from "../types";

export const dashboardGuide: HelpGuide = {
  title: { en: "Home dashboard", ar: "لوحة البداية" },
  purpose: {
    en: "Your daily starting point. It shows the health of the business at a glance — key numbers, recent activity, and shortcuts to the things you do most.",
    ar: "نقطة انطلاقك اليومية. تعرض حالة العمل في لمحة — الأرقام الرئيسية والنشاط الأخير واختصارات لأكثر ما تستخدمه.",
  },
  howItWorks: {
    en: "Every figure here is calculated live from real data you and your team enter elsewhere (sales, purchases, journals). It is read-only — to change a number, go to the page that owns it.",
    ar: "كل رقم هنا محسوب مباشرة من بيانات حقيقية تدخلونها في صفحات أخرى (المبيعات، المشتريات، القيود). الصفحة للعرض فقط — لتغيير رقم، انتقل إلى الصفحة التي يخصها.",
  },
  sections: [
    {
      heading: { en: "KPI cards", ar: "بطاقات المؤشرات" },
      body: {
        en: "The cards at the top summarise key figures with a comparison to the previous month.",
        ar: "البطاقات في الأعلى تلخّص الأرقام الرئيسية مع مقارنة بالشهر السابق.",
      },
      items: [
        {
          term: { en: "The small up/down delta", ar: "نسبة الصعود/الهبوط الصغيرة" },
          desc: {
            en: "How this month compares to last month. Green is usually good, but read it in context (rising expenses are not good).",
            ar: "مقارنة هذا الشهر بالشهر السابق. الأخضر جيد غالباً، لكن افهمه في سياقه (ارتفاع المصروفات ليس جيداً).",
          },
        },
      ],
    },
    {
      heading: { en: "Panels & shortcuts", ar: "اللوحات والاختصارات" },
      body: {
        en: "Below the cards are panels (top expenses, cash flow, recent journals) and a shortcuts rail to jump straight into common actions.",
        ar: "أسفل البطاقات لوحات (أعلى المصروفات، التدفق النقدي، أحدث القيود) وشريط اختصارات للانتقال مباشرة إلى الإجراءات الشائعة.",
      },
    },
  ],
  tasks: [
    {
      name: { en: "Start your day", ar: "ابدأ يومك" },
      steps: [
        { en: "Scan the KPI cards for anything unusual.", ar: "تصفّح بطاقات المؤشرات بحثاً عن أي شيء غير معتاد." },
        { en: "Check recent journals and activity to see what changed.", ar: "راجع أحدث القيود والنشاط لمعرفة ما تغيّر." },
        { en: "Use a shortcut or the sidebar to go where you need to work.", ar: "استخدم اختصاراً أو الشريط الجانبي للانتقال إلى حيث تعمل." },
      ],
    },
  ],
  tips: [
    { en: "Switch language any time from the top bar — the whole app, including this help, follows.", ar: "بدّل اللغة في أي وقت من الشريط العلوي — يتبعها التطبيق بالكامل بما في ذلك هذه المساعدة." },
  ],
  mistakes: [
    { en: "Don't treat the dashboard as a place to edit — it only reflects data entered elsewhere.", ar: "لا تعامل اللوحة كمكان للتعديل — هي تعكس فقط بيانات أُدخلت في صفحات أخرى." },
  ],
  related: [
    { to: "/accounting", label: { en: "Accounting", ar: "المحاسبة" } },
    { to: "/sales", label: { en: "Sales", ar: "المبيعات" } },
  ],
};

export const workflowsGuide: HelpGuide = {
  title: { en: "Workflows", ar: "مسارات العمل" },
  purpose: {
    en: "Design and run automated business processes — for example an approval chain or a multi-step procedure — without writing code.",
    ar: "صمّم وشغّل عمليات عمل آلية — مثل سلسلة موافقات أو إجراء متعدد الخطوات — دون كتابة برمجة.",
  },
  howItWorks: {
    en: "A workflow is a diagram of steps connected by arrows. You build it once; each time it 'starts', the system walks the steps in order, pausing for approvals where needed. This list shows every workflow you've built.",
    ar: "مسار العمل مخطط من خطوات تربطها أسهم. تبنيه مرة واحدة؛ وكلما 'بدأ'، ينفّذ النظام الخطوات بالترتيب متوقفاً عند الموافقات حين يلزم. تعرض هذه القائمة كل مسار بنيته.",
  },
  tasks: [
    {
      name: { en: "Open or create a workflow", ar: "افتح أو أنشئ مساراً" },
      steps: [
        { en: "Click a workflow in the list to open its canvas, or choose 'New'.", ar: "انقر مساراً في القائمة لفتح لوحته، أو اختر 'جديد'." },
        { en: "Build the steps, then save and run it.", ar: "ابنِ الخطوات ثم احفظ وشغّل." },
      ],
    },
  ],
  related: [
    { to: "/workflows/new", label: { en: "New workflow", ar: "مسار جديد" } },
  ],
};

export const workflowCanvasGuide: HelpGuide = {
  title: { en: "Workflow canvas", ar: "لوحة مسار العمل" },
  purpose: {
    en: "The drawing board where you build a process by placing steps and connecting them with arrows.",
    ar: "لوحة الرسم حيث تبني العملية بوضع الخطوات وربطها بالأسهم.",
  },
  howItWorks: {
    en: "Drag a step type from the palette onto the canvas, then drag from one step to another to connect them. Click any step to set its details in the side panel. Save bumps the version; running starts a live instance.",
    ar: "اسحب نوع خطوة من اللوحة الجانبية إلى مساحة الرسم، ثم اسحب من خطوة إلى أخرى لربطهما. انقر أي خطوة لضبط تفاصيلها في اللوحة الجانبية. الحفظ يرفع الإصدار، والتشغيل يبدأ نسخة حية.",
  },
  sections: [
    {
      heading: { en: "Step types", ar: "أنواع الخطوات" },
      items: [
        { term: { en: "Start / End", ar: "بداية / نهاية" }, desc: { en: "Where the process begins and finishes.", ar: "حيث تبدأ العملية وتنتهي." } },
        { term: { en: "Condition", ar: "شرط" }, desc: { en: "Splits the path based on a rule (e.g. amount over a limit).", ar: "يقسم المسار حسب قاعدة (مثل مبلغ يتجاوز حدّاً)." } },
        { term: { en: "Approval", ar: "موافقة" }, desc: { en: "Pauses until a person approves or rejects.", ar: "يتوقف حتى يوافق شخص أو يرفض." } },
      ],
    },
  ],
  tips: [
    { en: "Connect every step — a step with no path out will stall the process.", ar: "اربط كل خطوة — خطوة بلا مسار خارج ستوقف العملية." },
  ],
  related: [
    { to: "/workflows", label: { en: "All workflows", ar: "كل المسارات" } },
  ],
};

export const executionViewerGuide: HelpGuide = {
  title: { en: "Run viewer", ar: "عارض التشغيل" },
  purpose: {
    en: "Watch a single run of a workflow: which steps ran, what they produced, and where it is now (including anything waiting for your approval).",
    ar: "تابع تشغيلاً واحداً لمسار: أي خطوات نُفّذت، وما أنتجته، وأين هو الآن (بما في ذلك ما ينتظر موافقتك).",
  },
  howItWorks: {
    en: "The timeline lists each step in the order it ran, with its status and logs. When a step is an approval that's waiting, Approve/Reject buttons appear and your choice resumes the process.",
    ar: "يعرض الخط الزمني كل خطوة بترتيب تنفيذها مع حالتها وسجلّاتها. عندما تكون الخطوة موافقة منتظرة، يظهر زرّا الموافقة/الرفض، واختيارك يُكمل العملية.",
  },
  tasks: [
    {
      name: { en: "Approve a waiting step", ar: "وافق على خطوة منتظرة" },
      steps: [
        { en: "Find the step marked as waiting for approval.", ar: "ابحث عن الخطوة المعلّمة بانتظار الموافقة." },
        { en: "Review its details, then click Approve or Reject.", ar: "راجع تفاصيلها ثم انقر موافقة أو رفض." },
      ],
    },
  ],
  related: [
    { to: "/workflows", label: { en: "Workflows", ar: "المسارات" } },
  ],
};

export const einvoiceGuide: HelpGuide = {
  title: { en: "E-invoicing (ETA)", ar: "الفوترة الإلكترونية (مصلحة الضرائب)" },
  purpose: {
    en: "Send your sales invoices to the Egyptian Tax Authority (ETA) and track whether each one was accepted.",
    ar: "أرسل فواتير مبيعاتك إلى مصلحة الضرائب المصرية وتابع قبول كل فاتورة.",
  },
  howItWorks: {
    en: "When you invoice a sales order, a draft e-invoice is created here automatically. You then Submit it to ETA (it gets a unique ID), and Check status until it shows Valid. You never re-type the invoice — it carries the order's figures.",
    ar: "عند إصدار فاتورة لطلب مبيعات، تُنشأ هنا فاتورة إلكترونية كمسودة تلقائياً. ثم ترسلها إلى المصلحة (تحصل على معرّف فريد)، وتفحص الحالة حتى تظهر 'صالحة'. لا تعيد كتابة الفاتورة — فهي تحمل أرقام الطلب.",
  },
  sections: [
    {
      heading: { en: "Status", ar: "الحالة" },
      items: [
        { term: { en: "Draft", ar: "مسودة" }, desc: { en: "Recorded from the invoice, not yet sent.", ar: "سُجّلت من الفاتورة ولم تُرسل بعد." } },
        { term: { en: "Submitted", ar: "مُرسَلة" }, desc: { en: "Sent to ETA, awaiting validation.", ar: "أُرسلت للمصلحة بانتظار التحقق." } },
        { term: { en: "Valid", ar: "صالحة" }, desc: { en: "Accepted by ETA — you're done.", ar: "قُبلت من المصلحة — انتهيت." } },
      ],
    },
  ],
  tasks: [
    {
      name: { en: "File an invoice", ar: "قدّم فاتورة" },
      steps: [
        { en: "Find the draft e-invoice in the list.", ar: "ابحث عن الفاتورة المسودة في القائمة." },
        { en: "Click 'Submit to ETA'.", ar: "انقر 'إرسال للمصلحة'." },
        { en: "Click 'Check status' until it reads Valid.", ar: "انقر 'فحص الحالة' حتى تصبح صالحة." },
      ],
    },
  ],
  mistakes: [
    { en: "If no e-invoice appears, the source order hasn't been invoiced yet — invoice it in Sales first.", ar: "إن لم تظهر فاتورة إلكترونية، فالطلب المصدر لم تُصدر له فاتورة بعد — أصدرها في المبيعات أولاً." },
  ],
  related: [
    { to: "/sales", label: { en: "Sales orders", ar: "طلبات المبيعات" } },
    { to: "/accounting/vat-return", label: { en: "VAT return", ar: "إقرار الضريبة" } },
  ],
};

export const notificationsGuide: HelpGuide = {
  title: { en: "Notifications", ar: "الإشعارات" },
  purpose: {
    en: "A log of every message the system sent out — emails to customers, WhatsApp alerts — so you can confirm it was delivered and resend if it wasn't.",
    ar: "سجل بكل رسالة أرسلها النظام — بريد للعملاء، تنبيهات واتساب — لتتأكد من وصولها وتعيد الإرسال إن لزم.",
  },
  howItWorks: {
    en: "Messages are sent automatically by business events: invoicing an order emails the customer; a ticket breaching its SLA sends a WhatsApp alert. Each attempt is recorded as one row with its outcome. Nothing here breaks your work — a failed message is just logged for you to resend.",
    ar: "تُرسل الرسائل تلقائياً بأحداث العمل: إصدار فاتورة لطلب يرسل بريداً للعميل؛ وتجاوز تذكرة لمستوى الخدمة يرسل تنبيه واتساب. تُسجّل كل محاولة كصف بنتيجتها. لا شيء هنا يعطّل عملك — الرسالة الفاشلة تُسجَّل فقط لتعيد إرسالها.",
  },
  sections: [
    {
      heading: { en: "Status", ar: "الحالة" },
      items: [
        { term: { en: "Sent", ar: "مُرسَل" }, desc: { en: "The channel accepted the message.", ar: "قبلت القناة الرسالة." } },
        { term: { en: "Failed", ar: "فشل" }, desc: { en: "Delivery failed (e.g. channel not configured). Hover the status to see why, then Resend.", ar: "فشل الإرسال (مثل قناة غير مهيأة). مرّر فوق الحالة لمعرفة السبب ثم أعد الإرسال." } },
      ],
    },
  ],
  tasks: [
    {
      name: { en: "Resend a failed message", ar: "أعد إرسال رسالة فاشلة" },
      steps: [
        { en: "Filter the list by status 'Failed'.", ar: "صفِّ القائمة بالحالة 'فشل'." },
        { en: "Click 'Resend' on the row — a new attempt is logged.", ar: "انقر 'إعادة الإرسال' في الصف — تُسجَّل محاولة جديدة." },
      ],
    },
  ],
  tips: [
    { en: "Email and WhatsApp run offline-safe by default; connect a real provider in settings to deliver for real.", ar: "البريد والواتساب يعملان بأمان دون اتصال افتراضياً؛ اربط مزوّداً حقيقياً في الإعدادات للإرسال الفعلي." },
  ],
  related: [
    { to: "/sales", label: { en: "Sales orders", ar: "طلبات المبيعات" } },
    { to: "/crm/tickets", label: { en: "Support tickets", ar: "تذاكر الدعم" } },
  ],
};
