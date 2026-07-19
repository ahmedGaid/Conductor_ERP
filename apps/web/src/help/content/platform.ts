import type { HelpGuide } from "../types";

export const assistantGuide: HelpGuide = {
  title: { en: "Assistant", ar: "المساعد الذكي" },
  purpose: {
    en: "Ask about your business in plain language — sales, receivables, stock — and get a short answer with links to the records it used.",
    ar: "اسأل عن عملك بلغتك — المبيعات، التحصيل، المخزون — واحصل على إجابة موجزة مع روابط للسجلات التي استندت إليها.",
  },
  howItWorks: {
    en: "The assistant only reads data you're allowed to see (your branch and scope) and answers from real records — it never invents a number, and every figure links back to its source. It reads; it doesn't change anything.",
    ar: "يقرأ المساعد الذكي البيانات المسموح لك برؤيتها فقط (فرعك ونطاقك) ويجيب من سجلات حقيقية — لا يختلق رقماً أبداً، وكل قيمة ترتبط بمصدرها. إنه يقرأ فقط ولا يغيّر شيئاً.",
  },
  tasks: [
    {
      name: { en: "Ask a question", ar: "اطرح سؤالاً" },
      steps: [
        { en: "Type a question, or pick one of the suggestions.", ar: "اكتب سؤالاً، أو اختر أحد الاقتراحات." },
        { en: "Read the answer and open any linked record to verify it.", ar: "اقرأ الإجابة وافتح أي سجلّ مرتبط للتحقق منه." },
      ],
    },
  ],
  related: [
    { to: "/sales", label: { en: "Sales orders", ar: "أوامر البيع" } },
    { to: "/inventory/stock-on-hand", label: { en: "Stock on hand", ar: "الرصيد المتاح" } },
  ],
};

export const userGuideGuide: HelpGuide = {
  title: { en: "User Guide", ar: "دليل الاستخدام" },
  purpose: {
    en: "A task-based walkthrough of the app's core daily flows, plus a glossary of every Arabic product term — works fully offline, no images to rot.",
    ar: "شرح خطوة بخطوة لأهم مسارات العمل اليومية في التطبيق، مع قاموس لكل مصطلح عربي في المنتج — يعمل بلا اتصال بالإنترنت، وبلا صور قد تتقادم.",
  },
  howItWorks: {
    en: "Pick a journey from the list to see its numbered steps and what can go wrong; pick the glossary entry to look up any term used elsewhere in the app.",
    ar: "اختر مسارًا من القائمة لترى خطواته المرقّمة وما قد يحدث خطأ فيه؛ اختر المصطلحات لتبحث عن أي كلمة تراها في التطبيق.",
  },
};

export const knowledgeGuide: HelpGuide = {
  title: { en: "Knowledge base", ar: "قاعدة المعرفة" },
  purpose: {
    en: "Upload reference documents (policies, guides, price sheets) so the assistant can answer questions from them, with a citation back to the source.",
    ar: "ارفع مستندات مرجعية (سياسات، أدلة، قوائم أسعار) ليجيب المساعد الذكي من محتواها، مع رابط للمصدر.",
  },
  howItWorks: {
    en: "Upload a file and it's read, split, and indexed automatically — the status pill shows processing, ready, or failed. Once ready, the assistant can search it when answering a question. Deleting a document removes it from search immediately.",
    ar: "ارفع ملفاً فتتم قراءته وتقسيمه وفهرسته تلقائياً — تُظهر شارة الحالة: قيد المعالجة، جاهز، أو فشل. بمجرد أن يصبح جاهزاً، يمكن للمساعد البحث فيه عند الإجابة عن سؤال. حذف مستند يزيله من البحث فوراً.",
  },
  tasks: [
    {
      name: { en: "Add a document", ar: "أضف مستنداً" },
      steps: [
        { en: "Click 'Upload', pick a file, and optionally give it a title.", ar: "انقر 'رفع'، اختر ملفاً، وأضف عنواناً اختيارياً." },
        { en: "Wait for the status to reach 'Ready'.", ar: "انتظر حتى تصل الحالة إلى 'جاهز'." },
      ],
    },
    {
      name: { en: "Remove a document", ar: "احذف مستنداً" },
      steps: [
        { en: "Click delete on the row and confirm.", ar: "انقر حذف في الصف وأكّد." },
      ],
    },
  ],
  mistakes: [
    { en: "If a document shows 'Failed', it had no readable text (e.g. a scanned image with no text) — try a text-based file instead.", ar: "إن ظهر مستند بحالة 'فشل'، فهذا يعني عدم وجود نص قابل للقراءة (كصورة ممسوحة بلا نص) — جرّب ملفاً نصياً بدلاً منه." },
  ],
  related: [
    { to: "/assistant", label: { en: "Assistant", ar: "المساعد الذكي" } },
  ],
};

export const opsGuide: HelpGuide = {
  title: { en: "Assistant health", ar: "صحة المساعد" },
  purpose: {
    en: "What the assistant did, what it cost, and whether it's healthy.",
    ar: "ما فعله المساعد الذكي، وتكلفته، ومدى سلامته.",
  },
  howItWorks: {
    en: "Every call is logged automatically. Pick a window to see totals, a daily chart, top errors, and the latest quality check. Click a table row to see its steps.",
    ar: "يُسجَّل كل طلب تلقائياً. اختر فترة لرؤية الإجماليات، والرسم اليومي، وأكثر الأخطاء شيوعاً، وآخر فحص جودة. انقر صفاً في الجدول لرؤية خطواته.",
  },
  related: [
    { to: "/assistant/knowledge", label: { en: "Knowledge base", ar: "قاعدة المعرفة" } },
  ],
};

export const entityLinkGuide: HelpGuide = {
  title: { en: "Opening a linked record", ar: "فتح سجلّ مرتبط" },
  purpose: {
    en: "A brief stop while the app opens the record you clicked — an order, a journal entry, or another document referenced by its number.",
    ar: "محطة قصيرة بينما يفتح التطبيق السجلّ الذي نقرت عليه — طلب أو قيد أو مستند آخر مُشار إليه برقمه.",
  },
  howItWorks: {
    en: "Codes and numbers throughout the app (item SKUs, warehouses, order and journal numbers) are clickable. When you click one, the app looks up the record and takes you straight to its page. If nothing matches, you'll see a short note and a way back.",
    ar: "الرموز والأرقام في كل أنحاء التطبيق (أكواد الأصناف، المخازن، أرقام الطلبات والقيود) قابلة للنقر. عند النقر، يبحث التطبيق عن السجلّ وينقلك مباشرة إلى صفحته. وإن لم يوجد ما يطابقه، تظهر لك ملاحظة قصيرة وطريقة للعودة.",
  },
};

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
    { to: "/accounting", label: { en: "Accounting", ar: "المالية" } },
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

export const customFieldsGuide: HelpGuide = {
  title: { en: "Custom fields", ar: "الحقول المخصّصة" },
  purpose: {
    en: "Add your own fields to customers, items, or suppliers — they show up on the form, the table, and the record page without any code change.",
    ar: "أضف حقولك الخاصة للعملاء أو الأصناف أو الموردين — تظهر في النموذج والجدول وصفحة السجلّ دون أي تعديل برمجي.",
  },
  howItWorks: {
    en: "Only a System Admin can add or edit custom fields. Pick the entity, give the field a key and a bilingual label, choose its type, then save — it appears immediately on that entity's form and table. Deactivating a field hides it from new entries but keeps the values already saved on existing records.",
    ar: "فقط مسؤول النظام يمكنه إضافة أو تعديل الحقول المخصّصة. اختر الكيان، أعطِ الحقل مفتاحاً وتسمية بلغتين، اختر نوعه، ثم احفظ — يظهر فوراً في نموذج وجدول ذلك الكيان. تعطيل حقل يخفيه عن الإدخالات الجديدة لكنه يبقي القيم المحفوظة على السجلات الحالية.",
  },
  sections: [
    {
      heading: { en: "Field types", ar: "أنواع الحقول" },
      items: [
        { term: { en: "Text / Number / Date", ar: "نص / رقم / تاريخ" }, desc: { en: "Free-entry values of that type.", ar: "قيم حرة من ذلك النوع." } },
        { term: { en: "Choice", ar: "اختيار" }, desc: { en: "A fixed list of options you define.", ar: "قائمة ثابتة من الخيارات تحددها." } },
        { term: { en: "Money", ar: "مبلغ مالي" }, desc: { en: "A currency amount, formatted like any other money field.", ar: "مبلغ مالي، منسّق كأي حقل مالي آخر." } },
      ],
    },
  ],
  tasks: [
    {
      name: { en: "Add a field", ar: "أضف حقلاً" },
      steps: [
        { en: "Choose the entity (Customers, Items, or Suppliers).", ar: "اختر الكيان (عملاء، أصناف، أو موردون)." },
        { en: "Enter a key, both labels, and pick a type, then click 'Add field'.", ar: "أدخل مفتاحاً وكلا التسميتين واختر النوع، ثم انقر 'إضافة حقل'." },
      ],
    },
  ],
  related: [
    { to: "/settings/developers", label: { en: "Developers", ar: "المطوّرون" } },
  ],
};

export const developersGuide: HelpGuide = {
  title: { en: "Developers", ar: "المطوّرون" },
  purpose: {
    en: "Create role-bound API keys for integrations, and browse a truthful reference of every route a key can reach.",
    ar: "أنشئ مفاتيح API مرتبطة بدور للتكاملات، وتصفّح مرجعاً دقيقاً لكل مسار يمكن لمفتاح الوصول إليه.",
  },
  howItWorks: {
    en: "Only a System Admin can manage API keys. A key authenticates as the role it's bound to — nothing more. The secret is shown once at creation; copy it immediately, it can't be retrieved again. Revoking a key is immediate and permanent — anything using it starts getting 401 Unauthorized right away.",
    ar: "فقط مسؤول النظام يمكنه إدارة مفاتيح API. يوثّق المفتاح باسم الدور المرتبط به فقط. يُعرض السر مرة واحدة عند الإنشاء — انسخه فوراً، فلا يمكن استرجاعه لاحقاً. إلغاء مفتاح فوري ودائم — كل ما يستخدمه يبدأ بتلقي خطأ 401 غير مصرح فوراً.",
  },
  tasks: [
    {
      name: { en: "Create a key", ar: "أنشئ مفتاحاً" },
      steps: [
        { en: "Click 'Create key', name it, and choose the role it authenticates as.", ar: "انقر 'إنشاء مفتاح'، سمِّه، واختر الدور الذي يوثّق باسمه." },
        { en: "Copy the secret shown — it won't be shown again.", ar: "انسخ السر المعروض — لن يظهر مرة أخرى." },
      ],
    },
    {
      name: { en: "Revoke a key", ar: "ألغِ مفتاحاً" },
      steps: [
        { en: "Click 'Revoke' on the row and confirm.", ar: "انقر 'إلغاء' في الصف وأكّد." },
      ],
    },
  ],
  mistakes: [
    { en: "Lost the secret and didn't copy it? There's no way to recover it — revoke the key and create a new one.", ar: "فقدت السر ولم تنسخه؟ لا سبيل لاسترجاعه — ألغِ المفتاح وأنشئ آخر." },
  ],
  related: [
    { to: "/settings/custom-fields", label: { en: "Custom fields", ar: "الحقول المخصّصة" } },
  ],
};

export const aiUsageGuide: HelpGuide = {
  title: { en: "AI usage", ar: "استخدام المساعد الذكي" },
  purpose: {
    en: "Where the assistant's tokens and cost went this month, and how close each spend budget is to its limit.",
    ar: "أين ذهبت رموز المساعد الذكي وتكلفته هذا الشهر، ومدى قرب كل ميزانية إنفاق من حدّها.",
  },
  howItWorks: {
    en: "Only a System Admin can view this. Every figure is a straight total over calls already made — nothing here is estimated. Pick a month to see its totals, the split by provider and by user, and how spend compares to the configured budgets. 'View traces' opens the underlying call log for the same numbers. No usage yet doesn't mean something is broken — the app works fully without AI.",
    ar: "فقط مسؤول النظام يمكنه رؤية هذا. كل رقم هنا إجمالي مباشر لطلبات تمّت فعلاً — لا شيء هنا تقديري. اختر شهراً لرؤية إجمالياته، والتوزيع حسب المزوّد وحسب المستخدم، ومقارنة الإنفاق بالميزانيات المُعدّة. 'عرض السجلات' يفتح سجل الطلبات الأصلي لنفس الأرقام. عدم وجود استخدام لا يعني وجود عطل — يعمل التطبيق بكامل وظائفه دون المساعد الذكي.",
  },
  related: [
    { to: "/assistant/ops", label: { en: "Assistant health", ar: "صحة المساعد" } },
  ],
};

export const systemGuide: HelpGuide = {
  title: { en: "System", ar: "النظام" },
  purpose: {
    en: "A read-only operator panel — database, Redis, background workers, storage, backup freshness, and which environment variables are configured, all at a glance.",
    ar: "لوحة تشغيل للقراءة فقط — قاعدة البيانات وRedis وعمليات المعالجة الخلفية والتخزين وحداثة النسخ الاحتياطي، وأي متغيرات بيئة مُعدّة، كل ذلك في نظرة واحدة.",
  },
  howItWorks: {
    en: "Only a System Admin can view this panel. It refreshes automatically every 30 seconds, or use 'Refresh' for an immediate check. Environment variables show as Set/Unset only — the actual values never leave the server. There's no way to change configuration from here by design: edit .env and restart the app.",
    ar: "فقط مسؤول النظام يمكنه رؤية هذه اللوحة. تُحدَّث تلقائياً كل 30 ثانية، أو استخدم 'تحديث' لفحص فوري. تظهر متغيرات البيئة كـ مُعدّ/غير مُعدّ فقط — القيم الفعلية لا تغادر الخادم أبداً. لا توجد طريقة لتغيير الإعدادات من هنا بالتصميم: عدّل ملف .env وأعد تشغيل التطبيق.",
  },
  mistakes: [
    {
      en: "'Backup: Not configured' doesn't mean backups are failing — it means BACKUP_DIR isn't set yet. Register the nightly backup task (see the Runbook) to start tracking it here.",
      ar: "'النسخ الاحتياطي: غير مُعدّ' لا تعني فشل النسخ الاحتياطي — بل أن BACKUP_DIR غير مُعدّ بعد. سجّل مهمة النسخ الاحتياطي الليلية (انظر دليل التشغيل) لبدء تتبعها هنا.",
    },
    {
      en: "'Background workers: Degraded' with 0 workers just means no Celery worker is currently running — queued jobs (imports, reports, notifications) wait until one starts, nothing is lost.",
      ar: "'عمليات المعالجة الخلفية: أداء متدهور' مع 0 عامل تعني فقط عدم تشغيل أي عامل Celery حالياً — المهام المُصفوفة (الاستيراد والتقارير والإشعارات) تنتظر حتى يبدأ أحدها، دون فقدان شيء.",
    },
  ],
  related: [
    { to: "/settings/developers", label: { en: "Developers", ar: "المطوّرون" } },
  ],
};
