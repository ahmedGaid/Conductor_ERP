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
        en: "Active sessions are this account's signed-in devices — revoke one to sign that device out, or 'Sign out everywhere' to end them all. Suspending the user also signs out every device immediately. Below that, Sign-in history shows recent logins.",
        ar: "الجلسات النشطة هي أجهزة هذا الحساب المسجَّل دخولها — أبطل واحدة لتسجيل خروج ذلك الجهاز، أو «تسجيل الخروج من كل الأجهزة» لإنهائها جميعاً. إيقاف المستخدم يسجّل الخروج من كل الأجهزة فوراً أيضاً. وأسفل ذلك يعرض سجل الدخول عمليات الدخول الأخيرة.",
      },
    },
  ],
  related: [{ to: "/admin/users", label: { en: "All users", ar: "كل المستخدمين" } }],
};

export const rolesGuide: HelpGuide = {
  title: { en: "Roles", ar: "الأدوار" },
  purpose: {
    en: "A role is a named set of permissions. Assign a role to a user and they inherit exactly what that role can see and do — change the role once and every member updates.",
    ar: "الدور هو مجموعة مُسمّاة من الصلاحيات. عند إسناد دور لمستخدم يرث تماماً ما يمكن لهذا الدور رؤيته وفعله — غيّر الدور مرة واحدة فيتحدث كل أعضائه.",
  },
  howItWorks: {
    en: "Built-in roles (System Admin, Branch Manager, Accountant, Auditor) ship ready to use. Create a custom role from scratch or duplicate an existing one as a starting point, then tune its permissions.",
    ar: "تأتي الأدوار المدمجة (مدير النظام، مدير الفرع، المحاسب، المدقق) جاهزة للاستخدام. أنشئ دوراً مخصصاً من الصفر أو انسخ دوراً قائماً كنقطة بداية، ثم اضبط صلاحياته.",
  },
  sections: [
    {
      heading: { en: "Kinds of role", ar: "أنواع الأدوار" },
      items: [
        { term: { en: "Built-in", ar: "مدمج" }, desc: { en: "Shipped with the system; cannot be deleted.", ar: "يأتي مع النظام؛ لا يمكن حذفه." } },
        { term: { en: "Custom", ar: "مخصص" }, desc: { en: "Created by an admin; fully editable and removable.", ar: "أنشأه المسؤول؛ قابل للتعديل والحذف بالكامل." } },
      ],
    },
  ],
  tasks: [
    {
      name: { en: "Create a role", ar: "إنشاء دور" },
      steps: [
        { en: "Click New role and give it a name.", ar: "اضغط «دور جديد» وأعطه اسماً." },
        { en: "Optionally start from an existing role to copy its permissions.", ar: "اختيارياً ابدأ من دور قائم لنسخ صلاحياته." },
        { en: "Open the new role and tick the permissions it should have.", ar: "افتح الدور الجديد وحدّد الصلاحيات التي يجب أن يملكها." },
      ],
    },
  ],
  tips: [
    { en: "Duplicating a close role is faster than building one from scratch.", ar: "نسخ دور قريب أسرع من بناء دور من الصفر." },
  ],
  related: [{ to: "/admin/users", label: { en: "Users", ar: "المستخدمون" } }],
};

export const roleDetailGuide: HelpGuide = {
  title: { en: "Role editor", ar: "محرّر الدور" },
  purpose: {
    en: "Decide exactly what this role can do: which actions it has on each part of the system, how much data it sees, and how large a document it may approve.",
    ar: "حدّد بدقة ما يمكن لهذا الدور فعله: أي إجراءات يملكها على كل جزء من النظام، وكم من البيانات يراها، وحجم المستند الذي يمكنه اعتماده.",
  },
  howItWorks: {
    en: "Permissions are grouped by module. For each item you grant View, Create, Edit, Delete or Approve, and pick a data scope that limits which records the action reaches. Changes save as you make them.",
    ar: "الصلاحيات مُجمّعة حسب الوحدة. لكل عنصر تمنح عرض أو إنشاء أو تعديل أو حذف أو اعتماد، وتختار نطاق بيانات يحدّ من السجلات التي يطالها الإجراء. تُحفظ التغييرات فور إجرائها.",
  },
  sections: [
    {
      heading: { en: "Data scope", ar: "نطاق البيانات" },
      body: {
        en: "Scope narrows what a permission reaches — from all records down to only the user's own. The broadest scope wins if a user holds the permission through more than one role.",
        ar: "يُضيّق النطاق ما تطاله الصلاحية — من كل السجلات وصولاً إلى سجلات المستخدم نفسه فقط. يفوز النطاق الأوسع إذا حصل المستخدم على الصلاحية عبر أكثر من دور.",
      },
    },
    {
      heading: { en: "Approval limits", ar: "حدود الاعتماد" },
      body: {
        en: "Cap the amount this role may approve per document type. Leave it unlimited for no ceiling, or remove it so the role cannot approve that document at all.",
        ar: "حدّد سقف المبلغ الذي يمكن لهذا الدور اعتماده لكل نوع مستند. اتركه بلا حدود لإلغاء السقف، أو احذفه فلا يستطيع الدور اعتماد ذلك المستند إطلاقاً.",
      },
    },
  ],
  tips: [
    { en: "System Admin bypasses every check, so its permissions are shown read-only.", ar: "مدير النظام يتجاوز كل الفحوصات، لذا تُعرض صلاحياته للقراءة فقط." },
    { en: "Reassign a custom role's members before deleting it.", ar: "أعد إسناد أعضاء الدور المخصص قبل حذفه." },
  ],
  related: [{ to: "/admin/roles", label: { en: "All roles", ar: "كل الأدوار" } }],
};
