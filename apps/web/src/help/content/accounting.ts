import type { HelpGuide } from "../types";

export const chartOfAccountsGuide: HelpGuide = {
  title: { en: "Chart of accounts", ar: "دليل الحسابات" },
  purpose: {
    en: "The master list of 'buckets' your money is tracked in — cash, bank, sales revenue, expenses, and so on. Every financial transaction lands in one of these accounts.",
    ar: "القائمة الرئيسية لـ'الأوعية' التي تُتابَع فيها أموالك — النقد، البنك، إيرادات المبيعات، المصروفات، وغيرها. كل معاملة مالية تقع في أحد هذه الحسابات.",
  },
  howItWorks: {
    en: "Each account has a code, a name, and a type (Asset, Liability, Equity, Income, or Expense). The type decides how the account behaves and where it appears in your reports. Most accounts you need are seeded for you; add more as the business grows.",
    ar: "لكل حساب رمز واسم ونوع (أصل، التزام، حقوق ملكية، إيراد، مصروف). يحدد النوع سلوك الحساب وموضعه في تقاريرك. معظم الحسابات التي تحتاجها مُهيأة مسبقاً؛ أضف المزيد مع نمو العمل.",
  },
  sections: [
    {
      heading: { en: "Account types", ar: "أنواع الحسابات" },
      items: [
        { term: { en: "Asset", ar: "أصل" }, desc: { en: "What you own (cash, inventory, receivables).", ar: "ما تملكه (نقد، مخزون، ذمم مدينة)." } },
        { term: { en: "Liability", ar: "التزام" }, desc: { en: "What you owe (suppliers, VAT, loans).", ar: "ما عليك (موردون، ضريبة، قروض)." } },
        { term: { en: "Income / Expense", ar: "إيراد / مصروف" }, desc: { en: "Money earned / money spent during a period.", ar: "ما كُسب / ما أُنفق خلال فترة." } },
      ],
    },
    {
      heading: { en: "Postable", ar: "قابل للترحيل" },
      body: {
        en: "Only 'postable' accounts can receive transactions. Heading accounts that group others are not postable.",
        ar: "الحسابات 'القابلة للترحيل' فقط يمكنها استقبال المعاملات. الحسابات الرئيسية التي تجمع غيرها ليست قابلة للترحيل.",
      },
    },
  ],
  tasks: [
    {
      name: { en: "Add an account", ar: "أضف حساباً" },
      steps: [
        { en: "Fill the new-account form: code, name, and type.", ar: "املأ نموذج الحساب الجديد: الرمز والاسم والنوع." },
        { en: "Save. It's now available wherever accounts are chosen.", ar: "احفظ. صار متاحاً أينما تُختار الحسابات." },
      ],
    },
  ],
  tips: [
    { en: "Use a consistent numbering scheme (e.g. 1000s = assets, 4000s = income) so reports read cleanly.", ar: "استخدم ترقيماً منظّماً (مثلاً 1000 = أصول، 4000 = إيرادات) لتقرأ التقارير بوضوح." },
  ],
  mistakes: [
    { en: "Don't pick the wrong type — it changes which report the account shows up in and is hard to undo after posting.", ar: "لا تختر النوع الخطأ — فهو يغيّر التقرير الذي يظهر فيه الحساب ويصعب تصحيحه بعد الترحيل." },
  ],
  related: [
    { to: "/accounting/journals/new", label: { en: "New journal entry", ar: "قيد جديد" } },
    { to: "/accounting/trial-balance", label: { en: "Trial balance", ar: "ميزان المراجعة" } },
  ],
};

export const journalListGuide: HelpGuide = {
  title: { en: "Journal entries", ar: "القيود اليومية" },
  purpose: {
    en: "The diary of every financial transaction — both the ones you type by hand and the ones the system posts for you (from sales, purchases, inventory).",
    ar: "يومية كل معاملة مالية — تلك التي تكتبها يدوياً وتلك التي يرحّلها النظام تلقائياً (من المبيعات والمشتريات والمخزون).",
  },
  howItWorks: {
    en: "Each entry is a balanced set of lines: total debits equal total credits. Click any entry to see its lines. Entries are permanent records — you never edit a posted entry; you reverse it with a new one.",
    ar: "كل قيد مجموعة سطور متوازنة: مجموع المدين يساوي مجموع الدائن. انقر أي قيد لرؤية سطوره. القيود سجلات دائمة — لا تعدّل قيداً مُرحّلاً؛ بل تعكسه بقيد جديد.",
  },
  tasks: [
    {
      name: { en: "Review an entry", ar: "راجع قيداً" },
      steps: [
        { en: "Click an entry in the list.", ar: "انقر قيداً في القائمة." },
        { en: "Check its lines and that debits equal credits.", ar: "تحقق من سطوره وأن المدين يساوي الدائن." },
      ],
    },
  ],
  related: [
    { to: "/accounting/journals/new", label: { en: "New journal entry", ar: "قيد جديد" } },
    { to: "/accounting/general-ledger", label: { en: "General ledger", ar: "دفتر الأستاذ" } },
  ],
};

export const journalEntryGuide: HelpGuide = {
  title: { en: "New journal entry", ar: "قيد يومية جديد" },
  purpose: {
    en: "Record a financial transaction by hand — for example a bank fee, an owner's contribution, or a correction.",
    ar: "سجّل معاملة مالية يدوياً — مثل رسوم بنكية أو مساهمة مالك أو تصحيح.",
  },
  howItWorks: {
    en: "Add lines, putting each amount in either the Debit or Credit column against an account. The form shows running totals and only lets you post when the two sides are equal (the golden rule of double-entry).",
    ar: "أضف سطوراً، واضعاً كل مبلغ في عمود المدين أو الدائن مقابل حساب. يعرض النموذج المجاميع الجارية ولا يسمح بالترحيل إلا حين يتساوى الجانبان (القاعدة الذهبية للقيد المزدوج).",
  },
  sections: [
    {
      heading: { en: "The form", ar: "النموذج" },
      items: [
        { term: { en: "Date", ar: "التاريخ" }, desc: { en: "Must fall inside an open period.", ar: "يجب أن يقع داخل فترة مفتوحة." } },
        { term: { en: "Debit / Credit", ar: "مدين / دائن" }, desc: { en: "Each line uses one side only. Debits increase assets/expenses; credits increase income/liabilities.", ar: "كل سطر يستخدم جانباً واحداً فقط. المدين يزيد الأصول/المصروفات؛ والدائن يزيد الإيرادات/الالتزامات." } },
        { term: { en: "Cost center", ar: "مركز التكلفة" }, desc: { en: "Optional tag so you can report profit by department later.", ar: "وسم اختياري لتقرير الربح حسب القسم لاحقاً." } },
      ],
    },
  ],
  tasks: [
    {
      name: { en: "Post an entry", ar: "رحّل قيداً" },
      steps: [
        { en: "Set the date and a description.", ar: "حدّد التاريخ ووصفاً." },
        { en: "Add at least two lines so debits and credits balance.", ar: "أضف سطرين على الأقل ليتوازن المدين والدائن." },
        { en: "When the 'balanced' indicator is green, click Post.", ar: "حين يصبح مؤشر 'متوازن' أخضر، انقر ترحيل." },
      ],
    },
  ],
  examples: [
    { en: "Bank fee of 50: Debit 'Bank charges' 50, Credit 'Bank' 50.", ar: "رسوم بنكية 50: مدين 'مصاريف بنكية' 50، دائن 'البنك' 50." },
  ],
  mistakes: [
    { en: "Posting is blocked if the period is closed — change the date or ask an admin to open the period.", ar: "يُمنع الترحيل إذا كانت الفترة مغلقة — غيّر التاريخ أو اطلب من المسؤول فتح الفترة." },
    { en: "Don't try to fix a posted entry by editing — post a reversing entry instead.", ar: "لا تصحّح قيداً مُرحّلاً بالتعديل — رحّل قيداً عكسياً بدلاً من ذلك." },
  ],
  related: [
    { to: "/accounting", label: { en: "Chart of accounts", ar: "دليل الحسابات" } },
    { to: "/accounting/journals", label: { en: "All journal entries", ar: "كل القيود" } },
  ],
};

export const journalDetailGuide: HelpGuide = {
  title: { en: "Journal entry detail", ar: "تفاصيل القيد" },
  purpose: {
    en: "See everything about one posted entry: its lines, the accounts hit, and the amounts.",
    ar: "اطّلع على كل تفاصيل قيد مُرحّل: سطوره والحسابات المتأثرة والمبالغ.",
  },
  howItWorks: {
    en: "This is a permanent record, shown read-only. If something is wrong, post a reversing entry rather than changing this one.",
    ar: "هذا سجل دائم يُعرض للقراءة فقط. إن كان فيه خطأ، رحّل قيداً عكسياً بدلاً من تغييره.",
  },
  related: [
    { to: "/accounting/journals", label: { en: "All journal entries", ar: "كل القيود" } },
  ],
};

export const trialBalanceGuide: HelpGuide = {
  title: { en: "Trial balance", ar: "ميزان المراجعة" },
  purpose: {
    en: "A one-page check that your books are internally consistent: it lists every account's balance, and the two totals must match.",
    ar: "فحص من صفحة واحدة لاتساق دفاترك: يعرض رصيد كل حساب، ويجب أن يتساوى المجموعان.",
  },
  howItWorks: {
    en: "It sums all posted entries per account for the period you pick. Because every entry was balanced, total debits always equal total credits — a 'balanced' badge confirms it.",
    ar: "يجمع كل القيود المُرحّلة لكل حساب للفترة التي تختارها. ولأن كل قيد كان متوازناً، يتساوى دائماً مجموع المدين والدائن — وتؤكده شارة 'متوازن'.",
  },
  tasks: [
    {
      name: { en: "Check a period", ar: "افحص فترة" },
      steps: [
        { en: "Pick the period at the top.", ar: "اختر الفترة في الأعلى." },
        { en: "Confirm the totals match and the badge is green.", ar: "تأكد من تطابق المجاميع وأن الشارة خضراء." },
        { en: "Export to CSV/Excel if you need it outside the system.", ar: "صدّر إلى CSV/Excel إن احتجته خارج النظام." },
      ],
    },
  ],
  related: [
    { to: "/accounting/general-ledger", label: { en: "General ledger", ar: "دفتر الأستاذ" } },
    { to: "/accounting/balance-sheet", label: { en: "Balance sheet", ar: "الميزانية" } },
  ],
};

export const generalLedgerGuide: HelpGuide = {
  title: { en: "General ledger", ar: "دفتر الأستاذ" },
  purpose: {
    en: "The full history of one account — every transaction that touched it, with a running balance.",
    ar: "السجل الكامل لحساب واحد — كل معاملة أثّرت فيه مع رصيد جارٍ.",
  },
  howItWorks: {
    en: "Pick an account and a date range; the ledger lists each entry in order and keeps a running total so you can see exactly how the balance moved.",
    ar: "اختر حساباً ونطاق تاريخ؛ يعرض الدفتر كل قيد بالترتيب ويحتفظ بمجموع جارٍ لترى بدقة كيف تحرّك الرصيد.",
  },
  tasks: [
    {
      name: { en: "Trace an account", ar: "تتبّع حساباً" },
      steps: [
        { en: "Choose the account.", ar: "اختر الحساب." },
        { en: "Read down the running balance to find where it changed.", ar: "اقرأ الرصيد الجاري للأسفل لتجد أين تغيّر." },
      ],
    },
  ],
  related: [
    { to: "/accounting/trial-balance", label: { en: "Trial balance", ar: "ميزان المراجعة" } },
  ],
};

export const incomeStatementGuide: HelpGuide = {
  title: { en: "Income statement", ar: "قائمة الدخل" },
  purpose: {
    en: "Shows whether you made a profit or a loss over a period: income minus expenses.",
    ar: "تبيّن إن حقّقت ربحاً أم خسارة خلال فترة: الإيراد ناقص المصروف.",
  },
  howItWorks: {
    en: "It groups all income and expense accounts for the period you choose and shows the net result. You can filter by cost center to see one department's profit.",
    ar: "تجمع كل حسابات الإيراد والمصروف للفترة المختارة وتعرض النتيجة الصافية. ويمكنك التصفية حسب مركز التكلفة لرؤية ربح قسم واحد.",
  },
  tasks: [
    {
      name: { en: "View a department's profit", ar: "اعرض ربح قسم" },
      steps: [
        { en: "Pick the period.", ar: "اختر الفترة." },
        { en: "Choose a cost center in the filter.", ar: "اختر مركز تكلفة في المصفاة." },
      ],
    },
  ],
  related: [
    { to: "/accounting/balance-sheet", label: { en: "Balance sheet", ar: "الميزانية" } },
    { to: "/accounting/cost-centers", label: { en: "Cost centers", ar: "مراكز التكلفة" } },
  ],
};

export const balanceSheetGuide: HelpGuide = {
  title: { en: "Balance sheet", ar: "الميزانية العمومية" },
  purpose: {
    en: "A snapshot of what the business owns and owes on a given date: assets versus liabilities plus equity.",
    ar: "لقطة لما يملكه العمل وما عليه في تاريخ محدد: الأصول مقابل الالتزامات زائد حقوق الملكية.",
  },
  howItWorks: {
    en: "Assets must always equal liabilities plus equity (including this period's profit). A 'balanced' indicator confirms the accounting equation holds — it always will, because the ledger enforces it.",
    ar: "يجب أن تتساوى الأصول دائماً مع الالتزامات زائد حقوق الملكية (متضمنة ربح الفترة). يؤكد مؤشر 'متوازن' تحقّق المعادلة المحاسبية — وسيتحقق دائماً لأن الدفتر يفرضه.",
  },
  related: [
    { to: "/accounting/income-statement", label: { en: "Income statement", ar: "قائمة الدخل" } },
    { to: "/accounting/cash-flow", label: { en: "Cash flow", ar: "التدفق النقدي" } },
  ],
};

export const cashFlowGuide: HelpGuide = {
  title: { en: "Cash flow statement", ar: "قائمة التدفق النقدي" },
  purpose: {
    en: "Shows how your cash and bank balances moved over a period — what came in and what went out.",
    ar: "تبيّن كيف تحركت أرصدة نقدك وبنكك خلال فترة — ما دخل وما خرج.",
  },
  howItWorks: {
    en: "It tracks only the cash-type accounts: opening balance, plus money in, minus money out, equals closing balance — which reconciles exactly to the cash account in the ledger.",
    ar: "تتبع الحسابات النقدية فقط: الرصيد الافتتاحي زائد الداخل ناقص الخارج يساوي الرصيد الختامي — الذي يطابق تماماً حساب النقد في الدفتر.",
  },
  related: [
    { to: "/accounting/balance-sheet", label: { en: "Balance sheet", ar: "الميزانية" } },
  ],
};

export const vatReturnGuide: HelpGuide = {
  title: { en: "VAT return", ar: "إقرار ضريبة القيمة المضافة" },
  purpose: {
    en: "Works out how much VAT you owe the tax authority (or they owe you) for a period.",
    ar: "يحسب كم ضريبة قيمة مضافة تدين بها للمصلحة (أو تدين لك) عن فترة.",
  },
  howItWorks: {
    en: "It nets the VAT you charged customers (output VAT) against the recoverable VAT you paid suppliers (input VAT). A positive figure is payable; a negative one is a refund position.",
    ar: "يقاصّ الضريبة التي حصّلتها من العملاء (ضريبة المخرجات) مع الضريبة القابلة للاسترداد التي دفعتها للموردين (ضريبة المدخلات). الرقم الموجب مستحق الدفع، والسالب موقف استرداد.",
  },
  tasks: [
    {
      name: { en: "Prepare a return", ar: "حضّر إقراراً" },
      steps: [
        { en: "Pick the period (date range).", ar: "اختر الفترة (نطاق التاريخ)." },
        { en: "Read the net payable/refund figure.", ar: "اقرأ صافي المستحق/الاسترداد." },
        { en: "Export it for your filing.", ar: "صدّره لتقديمك." },
      ],
    },
  ],
  related: [
    { to: "/einvoice", label: { en: "E-invoicing", ar: "الفوترة الإلكترونية" } },
  ],
};

export const fixedAssetsGuide: HelpGuide = {
  title: { en: "Fixed assets", ar: "الأصول الثابتة" },
  purpose: {
    en: "Track long-lived items you bought (vehicles, equipment, computers) and spread their cost over their useful life through depreciation.",
    ar: "تابع الأصول طويلة العمر التي اشتريتها (مركبات، معدات، حواسيب) ووزّع تكلفتها على عمرها النافع عبر الإهلاك.",
  },
  howItWorks: {
    en: "Register an asset with its cost and useful life. Each month you run depreciation, which posts a small expense automatically. When you sell or scrap it, you dispose of it and the system books any gain or loss.",
    ar: "سجّل الأصل بتكلفته وعمره النافع. كل شهر تشغّل الإهلاك فيُرحّل مصروفاً صغيراً تلقائياً. وعند البيع أو الاستبعاد، تتخلّص منه فيقيّد النظام أي ربح أو خسارة.",
  },
  tasks: [
    {
      name: { en: "Run monthly depreciation", ar: "شغّل الإهلاك الشهري" },
      steps: [
        { en: "Open the depreciation run for the period.", ar: "افتح تشغيل الإهلاك للفترة." },
        { en: "Run it — entries post for all eligible assets, once each.", ar: "شغّله — تُرحّل القيود لكل الأصول المؤهلة، مرة لكل أصل." },
      ],
    },
  ],
  tips: [
    { en: "Depreciation is safe to run twice — it won't double-charge a period.", ar: "تشغيل الإهلاك آمن مرتين — لن يحمّل الفترة مرتين." },
  ],
  related: [
    { to: "/accounting/journals", label: { en: "Journal entries", ar: "القيود" } },
  ],
};

export const fixedAssetDetailGuide: HelpGuide = {
  title: { en: "Asset detail", ar: "تفاصيل الأصل" },
  purpose: {
    en: "Everything about one asset: its cost, accumulated depreciation, current book value, and history.",
    ar: "كل تفاصيل أصل واحد: تكلفته، مجمع إهلاكه، قيمته الدفترية الحالية، وتاريخه.",
  },
  howItWorks: {
    en: "Use this page to review an asset and to dispose of it when you sell or scrap it.",
    ar: "استخدم هذه الصفحة لمراجعة الأصل والتخلص منه عند بيعه أو استبعاده.",
  },
  tasks: [
    {
      name: { en: "Dispose of an asset", ar: "تخلّص من أصل" },
      steps: [
        { en: "Open the asset and click Dispose.", ar: "افتح الأصل وانقر تخلّص." },
        { en: "Enter the sale proceeds (or zero if scrapped).", ar: "أدخل حصيلة البيع (أو صفراً إن استُبعد)." },
        { en: "The system books the gain or loss automatically.", ar: "يقيّد النظام الربح أو الخسارة تلقائياً." },
      ],
    },
  ],
  related: [
    { to: "/accounting/assets", label: { en: "All assets", ar: "كل الأصول" } },
  ],
};

export const costCentersGuide: HelpGuide = {
  title: { en: "Cost centers", ar: "مراكز التكلفة" },
  purpose: {
    en: "Departments or projects you want to measure separately — so you can see the profit of, say, the Cairo branch versus the Alex branch.",
    ar: "أقسام أو مشاريع تريد قياسها بشكل منفصل — لترى ربح فرع القاهرة مقابل فرع الإسكندرية مثلاً.",
  },
  howItWorks: {
    en: "Create a cost center here, then tag journal lines with it as you post. Reports like the income statement can then be filtered by cost center. It's optional — untagged transactions still work normally.",
    ar: "أنشئ مركز تكلفة هنا، ثم وسِم سطور القيود به عند الترحيل. عندها يمكن تصفية تقارير مثل قائمة الدخل حسب مركز التكلفة. وهو اختياري — المعاملات غير الموسومة تعمل عادياً.",
  },
  related: [
    { to: "/accounting/income-statement", label: { en: "Income statement", ar: "قائمة الدخل" } },
  ],
};

export const bankReconciliationGuide: HelpGuide = {
  title: { en: "Bank reconciliation", ar: "التسوية البنكية" },
  purpose: {
    en: "Make sure your books agree with your actual bank statement — matching each line and catching anything missing.",
    ar: "تأكّد من توافق دفاترك مع كشف حسابك البنكي الفعلي — بمطابقة كل سطر واكتشاف أي نقص.",
  },
  howItWorks: {
    en: "Enter (or import) a bank statement, then auto-match its lines to your cash transactions. Bank-only items like fees or interest are booked with an adjustment. When both sides tie out exactly, you mark it reconciled.",
    ar: "أدخل (أو استورد) كشفاً بنكياً، ثم طابق سطوره آلياً مع معاملاتك النقدية. البنود البنكية فقط كالرسوم أو الفوائد تُقيَّد بتسوية. وحين يتطابق الجانبان تماماً، تعلّمه كمُسوّى.",
  },
  tasks: [
    {
      name: { en: "Reconcile a statement", ar: "سوِّ كشفاً" },
      steps: [
        { en: "Open the statement and click Auto-match.", ar: "افتح الكشف وانقر مطابقة آلية." },
        { en: "Book any fees/interest as an adjustment.", ar: "قيّد أي رسوم/فوائد كتسوية." },
        { en: "When the difference is zero, mark it reconciled.", ar: "حين يصبح الفرق صفراً، علّمه كمُسوّى." },
      ],
    },
  ],
  mistakes: [
    { en: "You can't mark it reconciled until the difference is exactly zero — find the missing line first.", ar: "لا يمكن تعليمه كمُسوّى حتى يصبح الفرق صفراً تماماً — جد السطر الناقص أولاً." },
  ],
  related: [
    { to: "/accounting/general-ledger", label: { en: "General ledger", ar: "دفتر الأستاذ" } },
  ],
};

export const bankStatementDetailGuide: HelpGuide = {
  title: { en: "Bank statement", ar: "كشف بنكي" },
  purpose: {
    en: "The matching screen for one statement: pair each bank line with your records and resolve the differences.",
    ar: "شاشة المطابقة لكشف واحد: قابِل كل سطر بنكي بسجلاتك وحلّ الفروق.",
  },
  howItWorks: {
    en: "Lines you've matched drop out of the 'outstanding' lists. Use Auto-match for the obvious pairs, then handle the rest by hand or with an adjustment.",
    ar: "السطور التي طابقتها تخرج من قوائم 'غير المسوّى'. استخدم المطابقة الآلية للأزواج الواضحة، ثم عالج الباقي يدوياً أو بتسوية.",
  },
  related: [
    { to: "/accounting/bank-reconciliation", label: { en: "All statements", ar: "كل الكشوف" } },
  ],
};

export const budgetsGuide: HelpGuide = {
  title: { en: "Budgets", ar: "الموازنات" },
  purpose: {
    en: "Set a financial plan for the year and compare it against what actually happened.",
    ar: "ضع خطة مالية للسنة وقارنها بما حدث فعلاً.",
  },
  howItWorks: {
    en: "Create a budget for a fiscal year, then enter a planned amount per account and period. The variance report shows actual minus budget so you can spot where you're over or under.",
    ar: "أنشئ موازنة لسنة مالية، ثم أدخل مبلغاً مخططاً لكل حساب وفترة. يعرض تقرير الانحراف الفعلي ناقص المخطط لترصد أين تجاوزت أو قصّرت.",
  },
  tasks: [
    {
      name: { en: "Create a budget", ar: "أنشئ موازنة" },
      steps: [
        { en: "Add a budget for the fiscal year.", ar: "أضف موازنة للسنة المالية." },
        { en: "Open it and enter planned amounts per account.", ar: "افتحها وأدخل المبالغ المخططة لكل حساب." },
      ],
    },
  ],
  related: [
    { to: "/accounting/income-statement", label: { en: "Income statement", ar: "قائمة الدخل" } },
  ],
};

export const budgetDetailGuide: HelpGuide = {
  title: { en: "Budget detail", ar: "تفاصيل الموازنة" },
  purpose: {
    en: "Enter the plan line by line and read the budget-vs-actual variance.",
    ar: "أدخل الخطة سطراً بسطر واقرأ انحراف المخطط مقابل الفعلي.",
  },
  howItWorks: {
    en: "Type a planned amount for each account/period; entering zero removes a line. Switch the period filter to compare a single month or the whole year.",
    ar: "اكتب مبلغاً مخططاً لكل حساب/فترة؛ إدخال صفر يحذف السطر. بدّل مصفاة الفترة لمقارنة شهر واحد أو السنة كاملة.",
  },
  related: [
    { to: "/accounting/budgets", label: { en: "All budgets", ar: "كل الموازنات" } },
  ],
};

export const reportBuilderGuide: HelpGuide = {
  title: { en: "Report builder", ar: "منشئ التقارير" },
  purpose: {
    en: "Build your own saved reports over the ledger — pick the accounts, dates, and grouping you care about — and optionally have them generated on a schedule.",
    ar: "ابنِ تقاريرك المحفوظة على الدفتر — اختر الحسابات والتواريخ والتجميع المهم لك — واختر توليدها وفق جدول إن شئت.",
  },
  howItWorks: {
    en: "Create a definition (what to include and how to group it), save it, then Run it any time to see a table you can export. Add a schedule (daily/weekly/monthly) to have the system write the export to disk automatically.",
    ar: "أنشئ تعريفاً (ماذا تُضمّن وكيف تجمّعه)، احفظه، ثم شغّله في أي وقت لرؤية جدول يمكنك تصديره. أضف جدولاً (يومي/أسبوعي/شهري) ليكتب النظام التصدير على القرص تلقائياً.",
  },
  sections: [
    {
      heading: { en: "Definition fields", ar: "حقول التعريف" },
      items: [
        { term: { en: "Account type / codes", ar: "نوع/رموز الحسابات" }, desc: { en: "Narrow the report to the accounts you want.", ar: "ضيّق التقرير على الحسابات التي تريدها." } },
        { term: { en: "Group by", ar: "التجميع حسب" }, desc: { en: "By account (balances) or by period (activity over time).", ar: "حسب الحساب (الأرصدة) أو حسب الفترة (النشاط عبر الزمن)." } },
        { term: { en: "Schedule", ar: "الجدول" }, desc: { en: "Optional — daily/weekly/monthly auto-generation.", ar: "اختياري — توليد تلقائي يومي/أسبوعي/شهري." } },
      ],
    },
  ],
  tasks: [
    {
      name: { en: "Build and run a report", ar: "ابنِ تقريراً وشغّله" },
      steps: [
        { en: "Fill the definition form and Save.", ar: "املأ نموذج التعريف واحفظ." },
        { en: "Click Run on the saved definition.", ar: "انقر تشغيل على التعريف المحفوظ." },
        { en: "Export the result if you need CSV/Excel.", ar: "صدّر النتيجة إن احتجت CSV/Excel." },
      ],
    },
  ],
  related: [
    { to: "/accounting/trial-balance", label: { en: "Trial balance", ar: "ميزان المراجعة" } },
  ],
};
