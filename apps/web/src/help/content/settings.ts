import type { HelpGuide } from "../types";

// Help guides for the personalization (Settings) pages. Plain-language and bilingual, like the rest.

const personalNote: HelpGuide["howItWorks"] = {
  en: "These are your personal preferences. They follow you on this account and never change anyone else's experience.",
  ar: "هذه تفضيلاتك الشخصية. ترافق حسابك ولا تغيّر تجربة أي مستخدم آخر.",
};

export const settingsProfileGuide: HelpGuide = {
  title: { en: "Profile", ar: "الملف الشخصي" },
  purpose: {
    en: "Your display name, contact details, language and how dates and times are shown to you.",
    ar: "اسمك الظاهر وبيانات التواصل واللغة وطريقة عرض التواريخ والأوقات لك.",
  },
  howItWorks: personalNote,
  sections: [
    {
      heading: { en: "Language & formats", ar: "اللغة والصيغ" },
      body: {
        en: "Choose Arabic or English (or Auto to follow the organization default), your time zone, and date/time formats. Changes apply instantly.",
        ar: "اختر العربية أو الإنجليزية (أو تلقائي لاتباع إعداد المؤسسة)، ومنطقتك الزمنية، وصيغ التاريخ والوقت. تُطبّق التغييرات فوراً.",
      },
    },
  ],
  tips: [
    { en: "Leave language on Auto to inherit whatever the administrator sets for the company.", ar: "اترك اللغة على «تلقائي» لتتبع ما يحدده المسؤول للمؤسسة." },
  ],
  related: [{ to: "/settings/appearance", label: { en: "Appearance", ar: "المظهر" } }],
};

export const settingsAppearanceGuide: HelpGuide = {
  title: { en: "Appearance", ar: "المظهر" },
  purpose: {
    en: "Make the workspace yours: light or dark mode, an accent colour, layout density, text size and sidebar style.",
    ar: "اجعل مساحة العمل خاصة بك: الوضع الفاتح أو الداكن، ولون مميّز، وكثافة التخطيط، وحجم النص، ونمط الشريط الجانبي.",
  },
  howItWorks: {
    en: "Each choice applies immediately and is remembered for next time. The accent only recolours in-page elements (like links); the core black brand of buttons and navigation stays consistent.",
    ar: "كل اختيار يُطبّق فوراً ويُحفظ للمرة القادمة. اللون المميّز يلوّن عناصر الصفحة فقط (مثل الروابط)؛ أما الهوية السوداء للأزرار والتنقل فتبقى ثابتة.",
  },
  sections: [
    {
      heading: { en: "Theme & accent", ar: "السمة واللون المميّز" },
      items: [
        { term: { en: "Theme", ar: "السمة" }, desc: { en: "Light, Dark, or System (follows your device).", ar: "فاتح أو داكن أو حسب الجهاز." } },
        { term: { en: "Accent", ar: "اللون المميّز" }, desc: { en: "Six presets; black keeps it fully monochrome.", ar: "ستة ألوان جاهزة؛ الأسود يبقيه أحادي اللون بالكامل." } },
      ],
    },
  ],
  tips: [
    { en: "Compact density and Small text fit more on screen; Large text improves readability.", ar: "الكثافة المضغوطة والنص الصغير يعرضان محتوى أكثر؛ النص الكبير يحسّن الوضوح." },
  ],
  related: [{ to: "/settings/accessibility", label: { en: "Accessibility", ar: "الوصول" } }],
};

export const settingsDashboardGuide: HelpGuide = {
  title: { en: "Dashboard", ar: "لوحة البداية" },
  purpose: {
    en: "Choose the page you land on after signing in, and which dashboard panels you see and in what order.",
    ar: "اختر الصفحة التي تبدأ منها بعد تسجيل الدخول، وأي لوحات تظهر لك وبأي ترتيب.",
  },
  howItWorks: personalNote,
  sections: [
    {
      heading: { en: "Widgets", ar: "اللوحات" },
      body: {
        en: "Use the arrows to reorder a panel and the switch to hide or show it. The Home dashboard reflects your choices.",
        ar: "استخدم الأسهم لإعادة ترتيب لوحة والمفتاح لإخفائها أو إظهارها. تعكس لوحة البداية اختياراتك.",
      },
    },
  ],
  related: [{ to: "/", label: { en: "Home dashboard", ar: "لوحة البداية" } }],
};

export const settingsNavigationGuide: HelpGuide = {
  title: { en: "Navigation", ar: "التنقل" },
  purpose: {
    en: "Pin the pages you use most so they appear in a Favorites group at the top of the sidebar.",
    ar: "ثبّت الصفحات التي تستخدمها كثيراً لتظهر ضمن مجموعة المفضلة أعلى الشريط الجانبي.",
  },
  howItWorks: personalNote,
  tasks: [
    {
      name: { en: "Pin a page", ar: "تثبيت صفحة" },
      steps: [
        { en: "Tap the star next to any destination.", ar: "اضغط النجمة بجوار أي وجهة." },
        { en: "It appears under Favorites in the sidebar immediately.", ar: "تظهر فوراً ضمن المفضلة في الشريط الجانبي." },
      ],
    },
  ],
};

export const settingsNotificationsGuide: HelpGuide = {
  title: { en: "Notifications", ar: "الإشعارات" },
  purpose: {
    en: "Decide how you want to be notified — in-app, by email — and how often you get a digest.",
    ar: "حدّد كيف تريد أن تُشعَر — داخل التطبيق أو بالبريد — وعدد مرات الملخص.",
  },
  howItWorks: personalNote,
  tips: [
    { en: "Desktop and sound alerts are saved here and will activate as those channels roll out.", ar: "تنبيهات سطح المكتب والصوت تُحفظ هنا وستُفعّل مع توفّر هذه القنوات." },
  ],
};

export const settingsAccessibilityGuide: HelpGuide = {
  title: { en: "Accessibility", ar: "إمكانية الوصول" },
  purpose: {
    en: "Options that make the app easier to read and use: larger text, higher contrast, reduced motion, and keyboard navigation hints.",
    ar: "خيارات تجعل التطبيق أسهل في القراءة والاستخدام: نص أكبر، تباين أعلى، حركة أقل، وتلميحات التنقل بلوحة المفاتيح.",
  },
  howItWorks: personalNote,
  tips: [
    { en: "Reduced motion removes animations — helpful if motion is distracting or causes discomfort.", ar: "تقليل الحركة يزيل الرسوم المتحركة — مفيد إن كانت الحركة مشتّتة أو مزعجة." },
  ],
  related: [{ to: "/settings/appearance", label: { en: "Appearance", ar: "المظهر" } }],
};

export const settingsOrganizationGuide: HelpGuide = {
  title: { en: "Organization defaults", ar: "إعدادات المؤسسة الافتراضية" },
  purpose: {
    en: "Administrator-only. Set company-wide defaults — language, theme, accent, landing page and company name — that every user inherits unless they choose their own.",
    ar: "للمسؤول فقط. حدّد إعدادات افتراضية للمؤسسة — اللغة والسمة واللون والصفحة الأولى واسم الشركة — يرثها كل مستخدم ما لم يختر إعداده الخاص.",
  },
  howItWorks: {
    en: "These are starting points, not locks: any user can override them in their own Settings. Only the System Admin can change this page.",
    ar: "هذه نقاط بداية وليست قيوداً: يمكن لأي مستخدم تجاوزها في إعداداته. ولا يمكن تغيير هذه الصفحة إلا لمسؤول النظام.",
  },
  related: [{ to: "/settings/appearance", label: { en: "Appearance", ar: "المظهر" } }],
};

export const settingsBranchesGuide: HelpGuide = {
  title: { en: "Branches", ar: "الفروع" },
  purpose: {
    en: "Administrator-only. Manage the company's branches — every user, and most business records, are scoped to one.",
    ar: "للمسؤول فقط. إدارة فروع الشركة — كل مستخدم، وأغلب السجلات، مرتبطة بفرع واحد منها.",
  },
  howItWorks: {
    en: "Add a branch with a short code and a name. Turning a branch off keeps its history but stops it from being assigned to new users or records. Only the System Admin can change this page.",
    ar: "أضف فرعاً برمز مختصر واسم. إيقاف الفرع يحتفظ بسجله لكنه يمنع تعيينه لمستخدمين أو سجلات جديدة. ولا يمكن تغيير هذه الصفحة إلا لمسؤول النظام.",
  },
  related: [{ to: "/settings/organization", label: { en: "Organization defaults", ar: "إعدادات المؤسسة" } }],
};

export const settingsCustomFieldsGuide: HelpGuide = {
  title: { en: "Custom fields", ar: "الحقول المخصّصة" },
  purpose: {
    en: "Administrator-only. Add your own fields to customers, items and suppliers — beyond the built-in ones — so records capture exactly what your business tracks.",
    ar: "للمسؤول فقط. أضف حقولك الخاصة إلى العملاء والأصناف والموردين — إلى جانب الحقول الجاهزة — لتلتقط السجلات ما يهم عملك بالضبط.",
  },
  howItWorks: {
    en: "Pick the record type, give the field a key and a bilingual (Arabic + English) label, choose its type and whether it's required, then Add. It appears on that record's create form and as an extra column in its list. Turning a field off hides it from new entry but keeps every value already saved. Only the System Admin can change this page.",
    ar: "اختر نوع السجل، وامنح الحقل مفتاحاً وتسمية بالعربية والإنجليزية، وحدّد نوعه وهل هو مطلوب، ثم اضغط «أضف». يظهر الحقل في نموذج إنشاء ذلك السجل وكعمود إضافي في قائمته. إيقاف الحقل يخفيه عن الإدخال الجديد لكنه يحتفظ بكل قيمة سبق حفظها. ولا يمكن تغيير هذه الصفحة إلا لمسؤول النظام.",
  },
  sections: [
    {
      heading: { en: "Field types", ar: "أنواع الحقول" },
      items: [
        { term: { en: "Text", ar: "نص" }, desc: { en: "A short free-text line.", ar: "سطر نص حر قصير." } },
        { term: { en: "Number", ar: "رقم" }, desc: { en: "A plain number.", ar: "رقم عادي." } },
        { term: { en: "Date", ar: "تاريخ" }, desc: { en: "A single calendar date.", ar: "تاريخ واحد من التقويم." } },
        { term: { en: "Choice", ar: "اختيار" }, desc: { en: "A pick-list — type the options separated by commas.", ar: "قائمة اختيار — اكتب الخيارات مفصولة بفواصل." } },
        { term: { en: "Money", ar: "مبلغ" }, desc: { en: "An amount, formatted in the organization currency.", ar: "مبلغ يُنسَّق بعملة المؤسسة." } },
      ],
    },
  ],
  tips: [
    { en: "Use the arrows to reorder fields — the order here is the order they appear on the form.", ar: "استخدم الأسهم لإعادة ترتيب الحقول — ترتيبها هنا هو ترتيب ظهورها في النموذج." },
    { en: "Deactivate rather than delete: it stops new entries without losing the history already captured.", ar: "استخدم الإيقاف بدل الحذف: يمنع الإدخالات الجديدة دون فقدان السجل الذي التُقط بالفعل." },
  ],
  related: [{ to: "/settings/organization", label: { en: "Organization defaults", ar: "إعدادات المؤسسة" } }],
};

export const settingsDevelopersGuide: HelpGuide = {
  title: { en: "Developers", ar: "المطوّرون" },
  purpose: {
    en: "Administrator-only. Create API keys so an outside system can call Conductor on your behalf, and read a truthful, always-current reference of the endpoints those keys can reach.",
    ar: "للمسؤول فقط. أنشئ مفاتيح واجهة برمجة ليستدعي نظام خارجي Conductor نيابةً عنك، واطّلع على مرجع صادق ومحدَّث دائماً بالمسارات التي تصل إليها تلك المفاتيح.",
  },
  howItWorks: {
    en: "A key is bound to a role, so it can do exactly what that role can do — no more. Add a key, pick its role, and copy the secret shown once (Conductor never shows it again — regenerate if you lose it). The calling system sends it on every request as the header Authorization: Api-Key <secret>. Revoke a key any time to cut off its access immediately. Only the System Admin can change this page.",
    ar: "يرتبط المفتاح بدور، فيفعل ما يفعله ذلك الدور بالضبط — لا أكثر. أضف مفتاحاً، واختر دوره، وانسخ المفتاح السري الذي يظهر مرة واحدة (لا يعرضه Conductor مجدداً — أعِد توليده إن فقدته). يُرسله النظام المستدعي في كل طلب ضمن الترويسة Authorization: Api-Key <secret>. ألغِ أي مفتاح في أي وقت لقطع وصوله فوراً. ولا يمكن تغيير هذه الصفحة إلا لمسؤول النظام.",
  },
  sections: [
    {
      heading: { en: "The reference panel", ar: "لوحة المرجع" },
      body: {
        en: "The list of endpoints below is generated from the app itself, so it's never out of date. Amounts are always sent and received as integer minor units (e.g. piastres), never decimals.",
        ar: "قائمة المسارات أدناه مولَّدة من التطبيق نفسه، فلا تكون قديمة أبداً. تُرسَل المبالغ وتُستقبَل دائماً كوحدات صغرى صحيحة (مثل القروش)، لا كأرقام عشرية.",
      },
    },
  ],
  tips: [
    { en: "Give each integration its own key with the narrowest role it needs — then you can revoke just that one without disturbing the others.", ar: "امنح كل تكامل مفتاحه الخاص بأضيق دور يحتاجه — عندها يمكنك إلغاؤه وحده دون التأثير على البقية." },
  ],
  mistakes: [
    { en: "Storing the secret somewhere public (a shared doc, a front-end bundle) — anyone who reads it holds that role's access. Keep it server-side, and revoke immediately if it leaks.", ar: "تخزين المفتاح السري في مكان عام (مستند مشترك، حزمة واجهة أمامية) — من يقرأه يملك وصول ذلك الدور. احفظه على الخادم، وألغِه فوراً إن تسرّب." },
  ],
  related: [{ to: "/settings/webhooks", label: { en: "Webhooks", ar: "الويب هوكس" } }],
};

export const settingsWebhooksGuide: HelpGuide = {
  title: { en: "Webhooks", ar: "الويب هوكس" },
  purpose: {
    en: "Administrator-only. The moment something happens in Conductor — an order confirmed, a payment received, a journal posted — send that event as an HTTP request to a URL you control. This is how you connect Conductor to Zapier, Make, Slack, a spreadsheet, or your own server, without Conductor needing to know that system exists.",
    ar: "للمسؤول فقط. لحظة حدوث شيء في Conductor — تأكيد طلب، استلام دفعة، ترحيل قيد — يُرسَل هذا الحدث كطلب HTTP إلى رابط تتحكم فيه أنت. بهذه الطريقة تربط Conductor بـ Zapier أو Make أو Slack أو جدول بيانات أو خادمك الخاص، دون أن يعرف Conductor شيئاً عن ذلك النظام.",
  },
  howItWorks: {
    en: "Paste a URL, tick the events it should fire on, and click Add. You'll see a signing secret exactly once — copy it now, Conductor never shows it again. From then on, every matching event becomes one POST to that URL, with a JSON body and two headers: X-Conductor-Event (the event name) and X-Conductor-Signature (a signature you can verify — see \"Verify the signature\" in Examples below). If the URL doesn't answer, delivery retries on its own; use \"Retry now\" under Deliveries to force an attempt immediately.",
    ar: "الصق رابطاً، اختر الأحداث التي تُشغّله، ثم اضغط «أضف». يظهر مفتاح التوقيع مرة واحدة فقط — انسخه الآن، لن يعرضه Conductor مجدداً. بعدها كل حدث مطابق يصبح طلب POST واحداً إلى ذلك الرابط، بمحتوى JSON وترويستين: X-Conductor-Event (اسم الحدث) وX-Conductor-Signature (توقيع يمكنك التحقق منه — انظر «التحقق من التوقيع» ضمن الأمثلة أدناه). إذا لم يستجب الرابط، تُعاد المحاولة تلقائياً؛ استخدم «إعادة المحاولة الآن» ضمن الإرساليات لإجبار محاولة فورية.",
  },
  sections: [
    {
      heading: { en: "What's in the request", ar: "ماذا يحتوي الطلب" },
      body: {
        en: "Every delivery is one HTTP POST with a JSON body shaped like this:",
        ar: "كل إرسال هو طلب POST واحد بمحتوى JSON بهذا الشكل:",
      },
      items: [
        { term: { en: "event", ar: "event" }, desc: { en: "The event name you subscribed to, e.g. sales.OrderConfirmed.", ar: "اسم الحدث الذي اشتركت فيه، مثل sales.OrderConfirmed." } },
        { term: { en: "occurred_at", ar: "occurred_at" }, desc: { en: "ISO timestamp of the moment it happened.", ar: "طابع زمني ISO للحظة وقوع الحدث." } },
        { term: { en: "entity / id", ar: "entity / id" }, desc: { en: "What kind of record and which one, e.g. sales_order / SO-2026-000037 — enough to look it up without parsing data.", ar: "نوع السجل ومعرّفه، مثل sales_order / SO-2026-000037 — يكفي لإيجاده دون تحليل data." } },
        { term: { en: "data", ar: "data" }, desc: { en: "The full record as Conductor holds it at that moment.", ar: "السجل الكامل كما يحفظه Conductor في تلك اللحظة." } },
      ],
    },
    {
      heading: { en: "The two headers", ar: "الترويستان" },
      items: [
        { term: { en: "X-Conductor-Event", ar: "X-Conductor-Event" }, desc: { en: "Same value as the payload's event field — lets you route the request before touching the body.", ar: "نفس قيمة حقل event في المحتوى — يتيح لك توجيه الطلب دون لمس المحتوى." } },
        { term: { en: "X-Conductor-Signature", ar: "X-Conductor-Signature" }, desc: { en: "sha256=<hex> — an HMAC-SHA256 of the raw request body, signed with your subscription's secret. Recompute it yourself and compare; if it doesn't match, the request didn't come from Conductor.", ar: "sha256=<hex> — توقيع HMAC-SHA256 لمحتوى الطلب الخام، موقّع بمفتاح اشتراكك. أعد حسابه بنفسك وقارنه؛ إن لم يتطابق فالطلب لم يأتِ من Conductor." } },
      ],
    },
  ],
  tasks: [
    {
      name: { en: "Send yourself a real test webhook (5 minutes)", ar: "أرسل لنفسك ويب هوك تجريبي حقيقي (5 دقائق)" },
      steps: [
        { en: "Open webhook.site (or any similar request-catcher tool) in a new tab — it gives you a free, unique URL and shows every request it receives, live.", ar: "افتح موقع webhook.site (أو أي أداة مشابهة لالتقاط الطلبات) في تبويب جديد — يمنحك رابطاً فريداً مجانياً ويعرض كل طلب يصله لحظياً." },
        { en: "Copy that URL, paste it into the URL field above, tick one event you can trigger easily — e.g. sales.OrderConfirmed — and click Add.", ar: "انسخ ذلك الرابط، الصقه في حقل الرابط أعلاه، اختر حدثاً واحداً يسهل تشغيله — مثل sales.OrderConfirmed — ثم اضغط «أضف»." },
        { en: "Copy the signing secret shown once — you'll need it if you try the signature-verification example below.", ar: "انسخ مفتاح التوقيع الذي يظهر مرة واحدة — ستحتاجه إن جرّبت مثال التحقق من التوقيع أدناه." },
        { en: "Go trigger that event for real — e.g. confirm a sales order — then come back here and open Deliveries next to your subscription.", ar: "اذهب وشغّل ذلك الحدث فعلياً — مثل تأكيد طلب بيع — ثم عد إلى هنا وافتح «الإرساليات» بجانب اشتراكك." },
        { en: "Switch to the webhook.site tab: the POST has landed, with the X-Conductor-Event / X-Conductor-Signature headers and the JSON body you just read about above.", ar: "انتقل إلى تبويب webhook.site: سيكون طلب POST قد وصل، بترويستَي X-Conductor-Event / X-Conductor-Signature والمحتوى JSON الذي شرحناه أعلاه." },
      ],
    },
  ],
  examples: [
    {
      en: "Example payload for sales.OrderConfirmed: {\"event\": \"sales.OrderConfirmed\", \"occurred_at\": \"2026-07-17T10:22:04Z\", \"entity\": \"sales_order\", \"id\": \"SO-2026-000037\", \"data\": { \"code\": \"SO-2026-000037\", \"customer\": \"ACME\", \"total_minor\": 85500 }}",
      ar: "مثال محتوى لحدث sales.OrderConfirmed: {\"event\": \"sales.OrderConfirmed\", \"occurred_at\": \"2026-07-17T10:22:04Z\", \"entity\": \"sales_order\", \"id\": \"SO-2026-000037\", \"data\": { \"code\": \"SO-2026-000037\", \"customer\": \"ACME\", \"total_minor\": 85500 }}",
    },
    {
      en: "Verify the signature in Python: expected = \"sha256=\" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest() — then compare it to the X-Conductor-Signature header with hmac.compare_digest, not ==.",
      ar: "التحقق من التوقيع بـ Python: expected = \"sha256=\" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest() — ثم قارنه بترويسة X-Conductor-Signature باستخدام hmac.compare_digest، وليس ==.",
    },
    {
      en: "Verify the signature in Node.js: const expected = \"sha256=\" + crypto.createHmac(\"sha256\", secret).update(rawBody).digest(\"hex\"); then compare with crypto.timingSafeEqual.",
      ar: "التحقق من التوقيع بـ Node.js: const expected = \"sha256=\" + crypto.createHmac(\"sha256\", secret).update(rawBody).digest(\"hex\"); ثم قارنه باستخدام crypto.timingSafeEqual.",
    },
    {
      en: "No-code option: point the URL at a Zapier \"Catch Hook\" trigger or a Make.com webhook module — each hands you the parsed fields to build the rest of your automation with, no server of your own required.",
      ar: "خيار بلا برمجة: وجّه الرابط إلى مشغّل «Catch Hook» في Zapier أو وحدة ويب هوك في Make.com — كلاهما يمنحك الحقول جاهزة لبناء بقية الأتمتة دون الحاجة لخادم خاص بك.",
    },
  ],
  tips: [
    { en: "The secret is shown only once, right after you add or regenerate a subscription — copy it immediately.", ar: "يظهر المفتاح مرة واحدة فقط، فور إضافة الاشتراك أو إعادة توليده — انسخه فوراً." },
    { en: "A failed delivery retries on its own at 1 minute, 5 minutes, 30 minutes, then 2 hours — after 5 attempts it's marked Failed and stops retrying. \"Retry now\" skips the wait.", ar: "الإرسال الفاشل تُعاد محاولته تلقائياً بعد دقيقة، 5 دقائق، 30 دقيقة، ثم ساعتين — بعد 5 محاولات يُعلَّم «فشل» وتتوقف إعادة المحاولة. «إعادة المحاولة الآن» تتخطى الانتظار." },
    { en: "The URL must be public — Conductor refuses localhost and private-network addresses. For local development, use a tunnel (e.g. ngrok) or a public catcher like webhook.site first.", ar: "يجب أن يكون الرابط عاماً — يرفض Conductor عناوين localhost والشبكات الخاصة. للتطوير المحلي استخدم نفقاً (مثل ngrok) أو أداة التقاط عامة مثل webhook.site أولاً." },
  ],
  mistakes: [
    { en: "Trusting the body without checking the signature — anyone who finds your URL can POST fake events to it. Always verify X-Conductor-Signature before acting on a delivery.", ar: "الوثوق بالمحتوى دون التحقق من التوقيع — أي شخص يعرف رابطك يمكنه إرسال أحداث مزيفة إليه. تحقق دائماً من X-Conductor-Signature قبل التصرف بناءً على أي إرسال." },
    { en: "Assuming delivery is instant and exactly-once — retries mean your endpoint may see the same event twice. Key your processing off the payload's id so a repeat is harmless.", ar: "افتراض أن الإرسال فوري ويحدث مرة واحدة فقط — إعادة المحاولة تعني أن نقطتك قد ترى نفس الحدث مرتين. اجعل معالجتك مبنية على id السجل حتى يكون التكرار غير ضار." },
    { en: "Testing against localhost — it will always fail Conductor's public-URL check. Use webhook.site or a tunnel first, then swap in your real endpoint.", ar: "الاختبار على localhost — سيفشل دائماً في فحص الرابط العام في Conductor. استخدم webhook.site أو نفقاً أولاً، ثم استبدله برابطك الحقيقي." },
  ],
  // --- Live tab: reacts to what the Webhooks page publishes via useSetHelpSignals ---
  alerts: [
    {
      when: (s) => s.subCount === 0,
      tone: "info",
      title: { en: "No webhooks yet", ar: "لا يوجد ويب هوك بعد" },
      body: {
        en: "Nothing is connected. Add a URL above — the checklist below walks you through sending yourself a real test delivery in a few minutes.",
        ar: "لا شيء متصل. أضف رابطاً أعلاه — القائمة أدناه ترشدك لإرسال إرسالية تجريبية حقيقية لنفسك خلال دقائق.",
      },
    },
    {
      when: (s) => s.secretJustShown === true,
      tone: "warn",
      title: { en: "Copy your secret now", ar: "انسخ مفتاحك الآن" },
      body: {
        en: "The signing secret on screen is shown only this once. Copy it before you close this — Conductor can't show it again, only regenerate a new one.",
        ar: "مفتاح التوقيع الظاهر على الشاشة يُعرض هذه المرة فقط. انسخه قبل الإغلاق — لا يستطيع Conductor عرضه مجدداً، بل توليد مفتاح جديد فقط.",
      },
    },
    {
      when: (s) => s.hasFailedDelivery === true,
      tone: "warn",
      title: { en: "A delivery failed", ar: "فشلت إرسالية" },
      body: {
        en: "One of your endpoints didn't answer with a success. It retries on its own (1m, 5m, 30m, 2h). Open Deliveries on that row to see the error and Retry now — usually the URL is down, or your signature check is rejecting it.",
        ar: "أحد نقاطك لم يستجب بنجاح. تُعاد المحاولة تلقائياً (دقيقة، 5، 30، ساعتان). افتح «الإرساليات» في ذلك الصف لرؤية الخطأ و«إعادة المحاولة الآن» — غالباً الرابط متوقف أو فحص توقيعك يرفضه.",
      },
    },
  ],
  checklist: {
    name: { en: "Send yourself your first webhook", ar: "أرسل لنفسك أول ويب هوك" },
    doneMessage: {
      en: "Done — you have a live webhook receiving real events. Point the URL at your own tool when you're ready, and delete this test one.",
      ar: "تم — لديك ويب هوك حيّ يستقبل أحداثاً حقيقية. وجّه الرابط إلى أداتك الخاصة حين تجهز، واحذف هذا التجريبي.",
    },
    steps: [
      {
        label: { en: "Get a test URL to catch the webhook", ar: "احصل على رابط تجريبي يلتقط الويب هوك" },
        detail: [
          {
            en: "Open webhook.site in a new browser tab. It's free and needs no sign-up.",
            ar: "افتح webhook.site في تبويب جديد. مجاني ولا يحتاج تسجيلاً.",
          },
          {
            en: "It instantly shows you a unique URL near the top, like https://webhook.site/abc-123. That page will display every request it receives, live.",
            ar: "يعرض لك فوراً رابطاً فريداً قرب الأعلى، مثل https://webhook.site/abc-123. وستعرض تلك الصفحة كل طلب يصلها لحظياً.",
          },
          {
            en: "Copy that URL, then come back to this page and paste it into the URL box above.",
            ar: "انسخ ذلك الرابط، ثم عد إلى هذه الصفحة والصقه في حقل الرابط أعلاه.",
          },
        ],
        hint: { en: "URL set. Now pick what should reach it.", ar: "تم ضبط الرابط. الآن اختر ما يصله." },
        done: (s) => s.urlTyped === true || (s.subCount as number) > 0,
      },
      {
        label: { en: "Choose one event to listen for", ar: "اختر حدثاً واحداً لتتابعه" },
        detail: [
          {
            en: "In the Events list above, tick a single event you can trigger yourself easily — sales.OrderConfirmed is a good first choice.",
            ar: "في قائمة الأحداث أعلاه، اختر حدثاً واحداً يسهل عليك تشغيله — sales.OrderConfirmed خيار أول جيد.",
          },
          {
            en: "Start with just one. You can always add more events to this webhook later.",
            ar: "ابدأ بواحد فقط. يمكنك دائماً إضافة أحداث أخرى لهذا الويب هوك لاحقاً.",
          },
        ],
        hint: { en: "Event chosen. Ready to create the webhook.", ar: "تم اختيار الحدث. جاهز لإنشاء الويب هوك." },
        done: (s) => s.eventsPicked === true || (s.subCount as number) > 0,
      },
      {
        label: { en: "Create the webhook", ar: "أنشئ الويب هوك" },
        detail: [
          {
            en: "Click the Add webhook button to save it. It becomes active straight away.",
            ar: "اضغط زر «إضافة ويب هوك» لحفظه. يصبح فعّالاً على الفور.",
          },
        ],
        done: (s) => (s.subCount as number) > 0,
      },
      {
        label: { en: "Copy your signing secret", ar: "انسخ مفتاح التوقيع" },
        detail: [
          {
            en: "A signing secret appears in a card right after you add the webhook — this is shown only once.",
            ar: "يظهر مفتاح توقيع في بطاقة فور إضافة الويب هوك — يُعرض مرة واحدة فقط.",
          },
          {
            en: "Copy it now and keep it somewhere safe. You'll use it later to check that a delivery really came from Conductor.",
            ar: "انسخه الآن واحفظه في مكان آمن. ستستخدمه لاحقاً للتأكد أن الإرسالية جاءت فعلاً من Conductor.",
          },
          {
            en: "Lost it? You can't see it again, but Regenerate secret on the row gives you a fresh one.",
            ar: "فقدته؟ لا يمكنك رؤيته مجدداً، لكن «تجديد المفتاح السري» في الصف يمنحك واحداً جديداً.",
          },
        ],
        hint: { en: "Secret saved. Now make it fire.", ar: "تم حفظ المفتاح. الآن اجعله ينطلق." },
        done: (s) => s.secretEverShown === true,
      },
      {
        label: { en: "Trigger it and watch it arrive", ar: "شغّله وراقب وصوله" },
        detail: [
          {
            en: "Go do the thing that fires your event — for sales.OrderConfirmed, open a sales order and confirm it.",
            ar: "اذهب وافعل ما يُطلق حدثك — لحدث sales.OrderConfirmed، افتح طلب بيع وأكّده.",
          },
          {
            en: "Come back here and click Deliveries on your webhook's row to see the attempt and its status.",
            ar: "عد إلى هنا واضغط «الإرساليات» في صف الويب هوك لرؤية المحاولة وحالتها.",
          },
          {
            en: "Switch to your webhook.site tab: the POST has landed there, with the X-Conductor-Event and X-Conductor-Signature headers and the JSON body.",
            ar: "انتقل إلى تبويب webhook.site: سيكون طلب POST قد وصل، بترويستَي X-Conductor-Event وX-Conductor-Signature ومحتوى JSON.",
          },
        ],
        done: (s) => s.hasDelivery === true,
      },
    ],
  },
  related: [{ to: "/settings/organization", label: { en: "Organization defaults", ar: "إعدادات المؤسسة" } }],
};
