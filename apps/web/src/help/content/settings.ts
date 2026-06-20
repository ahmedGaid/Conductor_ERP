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
