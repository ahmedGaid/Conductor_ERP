import type { HelpGuide } from "../types";

export const usersGuide: HelpGuide = {
  title: { en: "Users", ar: "المستخدمون" },
  purpose: {
    en: "Manage the people who can sign in: invite new users, assign roles and departments, and control each account's lifecycle.",
    ar: "إدارة الأشخاص الذين يمكنهم تسجيل الدخول: دعوة مستخدمين جدد، وإسناد الأدوار والأقسام، والتحكم في دورة حياة كل حساب.",
  },
  howItWorks: {
    en: "A role decides what a user can do (permissions); status decides whether they can sign in at all. Suspended and archived users keep their history but cannot log in.",
    ar: "الدور يحدد ما يمكن للمستخدم فعله (الصلاحيات)؛ والحالة تحدد ما إذا كان يمكنه تسجيل الدخول أساساً. المستخدمون الموقوفون والمؤرشفون يحتفظون بسجلهم لكن لا يمكنهم الدخول.",
  },
  sections: [
    {
      heading: { en: "Status", ar: "الحالة" },
      items: [
        { term: { en: "Active", ar: "نشط" }, desc: { en: "Can sign in and work normally.", ar: "يمكنه الدخول والعمل بشكل طبيعي." } },
        { term: { en: "Invited", ar: "مدعو" }, desc: { en: "Created with a temporary password, not yet signed in.", ar: "أُنشئ بكلمة مرور مؤقتة ولم يسجّل الدخول بعد." } },
        { term: { en: "Suspended", ar: "موقوف" }, desc: { en: "Blocked from signing in; can be reactivated.", ar: "ممنوع من الدخول؛ يمكن إعادة تفعيله." } },
        { term: { en: "Archived", ar: "مؤرشف" }, desc: { en: "Retired account kept for the record.", ar: "حساب متقاعد محفوظ للسجل." } },
      ],
    },
  ],
  tasks: [
    {
      name: { en: "Invite a user", ar: "دعوة مستخدم" },
      steps: [
        { en: "Click Invite user and fill in username, email, role.", ar: "اضغط «دعوة مستخدم» واملأ اسم المستخدم والبريد والدور." },
        { en: "Copy the one-time temporary password shown and share it securely.", ar: "انسخ كلمة المرور المؤقتة لمرة واحدة وشاركها بأمان." },
      ],
    },
  ],
  tips: [
    { en: "Select several rows to suspend, activate, or archive them in one action.", ar: "حدّد عدة صفوف لإيقافها أو تفعيلها أو أرشفتها دفعة واحدة." },
  ],
  related: [{ to: "/settings/organization", label: { en: "Organization defaults", ar: "إعدادات المؤسسة" } }],
};

export const userDetailGuide: HelpGuide = {
  title: { en: "User detail", ar: "تفاصيل المستخدم" },
  purpose: {
    en: "Everything about one user: profile, assigned role, the modules and permissions they get from it, recent sign-ins, and their activity.",
    ar: "كل شيء عن مستخدم واحد: الملف، والدور المُسند، والوحدات والصلاحيات الناتجة عنه، وعمليات الدخول الأخيرة، ونشاطه.",
  },
  howItWorks: {
    en: "Change the role and the module access and permissions update automatically — they are computed from the role, not set per user. Reset password issues a fresh one-time password.",
    ar: "غيّر الدور فتتحدث الوحدات والصلاحيات تلقائياً — فهي محسوبة من الدور وليست مضبوطة لكل مستخدم. إعادة التعيين تصدر كلمة مرور مؤقتة جديدة.",
  },
  sections: [
    {
      heading: { en: "Sessions", ar: "الجلسات" },
      body: {
        en: "Recent sign-in history for this account. To block access immediately, set the status to Suspended.",
        ar: "سجل عمليات الدخول الأخيرة لهذا الحساب. لمنع الوصول فوراً، اضبط الحالة على «موقوف».",
      },
    },
  ],
  related: [{ to: "/admin/users", label: { en: "All users", ar: "كل المستخدمين" } }],
};
