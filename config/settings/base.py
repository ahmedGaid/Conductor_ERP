"""Base settings shared by all environments.

Customer-hosted, single-tenant. No cloud-only dependencies. Values come from the
environment (.env) so the same code runs on a dev box or a Windows Server install.
"""
from pathlib import Path

import environ
from celery.schedules import crontab

# config/settings/base.py -> repo root is three parents up.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_IP_WHITELIST=(list, []),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
)

# Load .env if present (never required to exist in production where env is injected).
_env_file = BASE_DIR / ".env"
if _env_file.exists():
    environ.Env.read_env(str(_env_file))

# --- Core ---
SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
# VERSION is the single source of truth; APP_VERSION env var can still override (e.g. a hotfix
# build without bumping the file) but normally just mirrors it.
_version_file = BASE_DIR / "VERSION"
_file_version = _version_file.read_text().strip() if _version_file.exists() else "0.0.0"
APP_VERSION = env("APP_VERSION", default=_file_version)
IP_WHITELIST = env("DJANGO_IP_WHITELIST")  # empty list => allow all (dev)
CSP_POLICY = ""  # off by default; prod sets a real policy (see settings/prod.py)

# --- Applications ---
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
]
# ERP modules (modular monolith). Each is an isolated Django app under erp/.
LOCAL_APPS = [
    "erp.core",
    "erp.identity",
    "erp.audit",
    "erp.monitoring",
    "erp.workflow",
    "erp.forms",
    "erp.accounting",
    "erp.inventory",
    "erp.pricing",
    "erp.sales",
    "erp.purchasing",
    "erp.crm",
    "erp.einvoice",
    "erp.notifications",
    "erp.setup",
    "erp.assistant",
    "erp.imports",
    "erp.worksessions",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    # Correlation ID must wrap everything so every log/error/audit row carries it.
    "erp.core.middleware.CorrelationIdMiddleware",
    "erp.core.middleware.IpWhitelistMiddleware",
    # Adds Content-Security-Policy when settings.CSP_POLICY is non-empty (prod sets it; dev leaves
    # it off because the SPA is served by Vite, not Django, during development).
    "erp.core.middleware.ContentSecurityPolicyMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Activate the request's language from Accept-Language (sent by the web client to match the UI),
    # so DRF's built-in validation messages (e.g. an invalid choice) come back in the user's language
    # instead of always the LANGUAGE_CODE default. Must sit after Session and before Common.
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database ---
DATABASES = {
    "default": {
        **env.db_url("DATABASE_URL", default="postgresql://erp:erp@localhost:5432/erp"),
        "ATOMIC_REQUESTS": False,  # explicit transactions in services (repository pattern)
    }
}
# Use psycopg v3.
DATABASES["default"]["ENGINE"] = "django.db.backends.postgresql"

# --- Custom user (set before first migration so the swap is clean) ---
AUTH_USER_MODEL = "identity.User"

# --- Password hashing (argon2 first) ---
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
]

# --- i18n (Arabic-first; the UI defaults to ar/RTL) ---
LANGUAGE_CODE = "ar"
LANGUAGES = [("ar", "Arabic"), ("en", "English")]
TIME_ZONE = "Africa/Cairo"
USE_I18N = True
USE_TZ = True

# --- Static / media / storage ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGE_ROOT = Path(env("STORAGE_ROOT", default=str(BASE_DIR / "storage")))

# Optional: where nightly backups land (register-backup-task.ps1 -OutDir, or the docker
# backup.sh out-dir). Empty = "not configured" in the system status panel (FILE_19) — the app
# never writes here itself, it only reads timestamps off whatever the backup job already wrote.
BACKUP_DIR = env("BACKUP_DIR", default="")

# --- E-invoicing: Egyptian Tax Authority (ETA) ---
# Real ETA submission (einvoice-eta-live FILE_01). Every value is env-only and empty by default:
# an install with no credentials keeps using the simulated adapter and never touches the network.
# Environment URLs are documented in .env.example (verified 2026-07-20 against the official SDK,
# https://sdk.invoicing.eta.gov.eg/faq/) — they are NOT defaulted here, because silently pointing a
# misconfigured install at a real tax endpoint is the one mistake this module must never make.
ETA_ENV = env("ETA_ENV", default="")  # "sandbox" | "production"; empty = not configured
ETA_IDENTITY_URL = env("ETA_IDENTITY_URL", default="")  # OAuth2 issuer, e.g. https://id.preprod.eta.gov.eg
ETA_API_BASE_URL = env("ETA_API_BASE_URL", default="")  # document API, e.g. https://api.preprod.invoicing.eta.gov.eg
ETA_CLIENT_ID = env("ETA_CLIENT_ID", default="")
ETA_CLIENT_SECRET = env("ETA_CLIENT_SECRET", default="")
ETA_RIN = env("ETA_RIN", default="")  # the taxpayer's registration number (tax profile identity)
# Issuer tax profile (FILE_02): static company identity stamped on every ETA document. Not a secret,
# so env-only for now (no DB columns yet — a follow-up admin-config slice may move it in-app). Empty
# fields produce a structurally-complete-but-not-yet-valid document until the real profile is set.
ETA_ISSUER_NAME = env("ETA_ISSUER_NAME", default="")          # legal company name on the invoice
ETA_ACTIVITY_CODE = env("ETA_ACTIVITY_CODE", default="")      # ETA taxpayer activity code
ETA_BRANCH_ID = env("ETA_BRANCH_ID", default="")             # issuing branch id registered with ETA
ETA_ISSUER_COUNTRY = env("ETA_ISSUER_COUNTRY", default="EG")  # ISO country code
ETA_ISSUER_GOVERNATE = env("ETA_ISSUER_GOVERNATE", default="")
ETA_ISSUER_REGION_CITY = env("ETA_ISSUER_REGION_CITY", default="")
ETA_ISSUER_STREET = env("ETA_ISSUER_STREET", default="")
ETA_ISSUER_BUILDING_NO = env("ETA_ISSUER_BUILDING_NO", default="")
# Since 2026-07-21 the admin can enter these in-app (Settings → E-Invoicing); the env vars above stay
# a valid fallback. The in-app client secret is stored ENCRYPTED — this is the Fernet key for it.
# Empty = derive a key from DJANGO_SECRET_KEY (fine for dev; a SECRET_KEY rotation then invalidates
# the stored secret and the admin re-enters it). Set an explicit 44-char url-safe base64 Fernet key
# in production so the stored secret survives a SECRET_KEY rotation. Generate one with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ETA_SECRET_KEY = env("ETA_SECRET_KEY", default="")

# --- ETA document signing (FILE_03) ---
# The PKCS#12 (.pfx) soft certificate ETA requires to sign every Invoice v1.0. Key material — kept
# OUT of the repo: point ETA_SIGNING_PFX_PATH at a file the deploy places outside version control,
# or supply the .pfx base64-encoded via ETA_SIGNING_PFX_BASE64 (e.g. from a secret manager). With
# neither set, documents go out unsigned (simulated/unconfigured path) and never reach ETA.
ETA_SIGNING_PFX_PATH = env("ETA_SIGNING_PFX_PATH", default="")
ETA_SIGNING_PFX_BASE64 = env("ETA_SIGNING_PFX_BASE64", default="")
ETA_SIGNING_PFX_PASSWORD = env("ETA_SIGNING_PFX_PASSWORD", default="")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "erp.identity.authentication.ApiKeyAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "EXCEPTION_HANDLER": "erp.core.exceptions.drf_exception_handler",
    # Rate limiting (abuse / brute-force protection). Per-IP for anonymous traffic (login/token),
    # per-user for authenticated traffic. Rates are env-tunable; dev/test disables them (see dev.py)
    # so the suite isn't throttled. Uses the default cache backend.
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "erp.identity.authentication.ApiKeyRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("DRF_THROTTLE_ANON", default="60/min"),
        "user": env("DRF_THROTTLE_USER", default="1000/min"),
        # Dedicated brute-force cap for the login endpoint (per-IP; sits under the anon rate).
        "login": env("DRF_THROTTLE_LOGIN", default="5/min"),
        # API keys are integration credentials, not interactive sessions — a distinct scope so one
        # runaway integration can't be tuned by (or exhaust) the human user rate.
        "api_key": env("DRF_THROTTLE_API_KEY", default="300/min"),
    },
}

# --- JWT (access/refresh) ---
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    # With the token_blacklist app installed, every issued refresh token is tracked as an
    # OutstandingToken (so it can be listed as a session and revoked); a rotated-out token is
    # blacklisted so it can't be replayed.
    "BLACKLIST_AFTER_ROTATION": True,
}

# --- Celery (Redis / Memurai) ---
_redis_url = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = _redis_url
CELERY_RESULT_BACKEND = _redis_url
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True  # recover jobs after a worker crash
CELERY_RESULT_EXTENDED = True
CELERY_TIMEZONE = TIME_ZONE  # beat crontab times below are Africa/Cairo, not UTC
# T5.9: ``assistant.run_detached_stream`` is routed to its own queue via the task decorator
# (``@shared_task(..., queue="ai_stream")``) so a long batch job already queued (import, scheduled
# report) can never sit in front of a live chat turn. Redis needs no predeclared queue — the
# worker just has to be started listening on it too: see deploy/windows/install-services.ps1
# (``-Q celery,ai_stream``) and RUNBOOK.md "Detached AI streaming".

# Periodic jobs (Celery beat). The scheduled-report task fires hourly and itself decides which saved
# report definitions are due (daily/weekly/monthly), writing their CSV exports to REPORTS_DIR.
CELERY_BEAT_SCHEDULE = {
    "run-scheduled-reports": {
        "task": "accounting.run_scheduled_reports",
        "schedule": 3600.0,  # seconds — hourly sweep
    },
    "send-ai-digests": {
        "task": "assistant.send_ai_digests",
        "schedule": crontab(hour=7, minute=0),  # 07:00 Africa/Cairo daily; task decides who's due
    },
    "send-ai-weekly-report": {
        "task": "assistant.send_ai_weekly_report",
        "schedule": crontab(hour=7, minute=30, day_of_week=1),  # Monday 07:30 Africa/Cairo
    },
    "retry-due-webhooks": {
        "task": "notifications.retry_due_webhooks",
        "schedule": 60.0,  # seconds — check for elapsed backoff windows every minute
    },
    "reconcile-einvoice-submissions": {
        "task": "einvoice.reconcile_submitted",
        "schedule": 300.0,  # seconds — check every 5 minutes for elapsed poll-backoff windows
    },
    "run-scheduled-workflow-triggers": {
        "task": "workflow.run_scheduled_triggers",
        "schedule": crontab(hour=7, minute=15),  # 07:15 Africa/Cairo daily
    },
}

# Where scheduled report exports are written.
REPORTS_DIR = STORAGE_ROOT / "reports"

# --- Email / notifications ---
# The notifications module's email channel sends through Django's email framework. Offline-safe by
# default: the console backend prints messages and never touches the network. In production, point
# EMAIL_BACKEND at SMTP via env (host/port/credentials) — the adapter surface is unchanged.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="conductor@example.com")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

REDIS_URL = _redis_url

# --- AI assistant (plan session 02; optional layer — see DECISIONS.md "AI 2026-07") ---
# Off unless an API key is present: a customer install with no key runs fully, AI UI hidden.
# Keys live in env only, never in code or the DB. Four providers behind one seam
# (erp.assistant.client): Anthropic (Claude), Google (Gemini), Mistral, Groq. Any key you set joins
# an automatic FAILOVER CHAIN — requests try the preferred provider first and fall to the next
# available one if it is down / rate-limited / erroring. Set ASSISTANT_PROVIDER=<name> to force a
# specific provider to the front of that chain; leave "" to use the built-in preference order.
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GROQ_API_KEY = env("GROQ_API_KEY", default="")  # Groq inference (OpenAI-compatible; Llama-4 vision)
MISTRAL_API_KEY = env("MISTRAL_API_KEY", default="")  # Mistral (OpenAI-compatible; Pixtral vision)
ASSISTANT_PROVIDER = env("ASSISTANT_PROVIDER", default="")  # "" = auto chain; else this one first
ASSISTANT_ENABLED = env.bool(
    "ASSISTANT_ENABLED",
    default=bool(ANTHROPIC_API_KEY or GEMINI_API_KEY or GROQ_API_KEY or MISTRAL_API_KEY),
)
ASSISTANT_MODEL = env("ASSISTANT_MODEL", default="")  # "" = the provider's default model
ASSISTANT_MAX_TOKENS = env.int("ASSISTANT_MAX_TOKENS", default=4096)  # per-request cost cap
ASSISTANT_RAG_EMBEDDINGS = env.bool("ASSISTANT_RAG_EMBEDDINGS", default=False)  # off = FTS-only search
# ai-reliability T3.1: when on, knowledge search's semantic arm runs in Postgres via the pgvector
# `<=>` operator over an HNSW-indexed `embedding_v` column, instead of the Python cosine loop. Off
# by default and a hard no-op unless the `vector` extension + column exist (migration 0010 skips
# both when the server lacks the extension), so installs without pgvector keep working unchanged.
ASSISTANT_PGVECTOR = env.bool("ASSISTANT_PGVECTOR", default=False)

# ai-reliability T5.9 (Twenty study 2026-07-16): when on, a chat/agent turn runs inside a Celery
# worker instead of the HTTP request — it survives page refresh, network drop, and worker restart
# (claim + Redis relay + heartbeat + reap; see erp/assistant/services/stream_relay.py). Off by
# default: an install with no worker running (or CELERY_TASK_ALWAYS_EAGER, as in CI) keeps using
# the in-request path unchanged, and existing tests are unaffected. Flip on once a worker is
# confirmed running (see RUNBOOK.md "Detached AI streaming").
ASSISTANT_DETACHED_STREAMING = env.bool("ASSISTANT_DETACHED_STREAMING", default=False)

# ai-reliability T3.5: when on, knowledge search's fused top candidates are rescored by an LLM
# relevance pass before the top-K enter the prompt (see erp/assistant/services/rerank.py). Off by
# default and eval-gated — flip on only once evals/results/rerank_decision.json records a real
# nDCG lift within the latency budget (T3.5 step 3); the ambiguity gap below skips the extra call
# entirely when the fused top pick is already a clear winner (RRF score units — see
# rerank._ambiguous docstring for why this is a tuned constant, not a statistical threshold).
ASSISTANT_RERANK = env.bool("ASSISTANT_RERANK", default=False)
ASSISTANT_RERANK_AMBIGUITY_GAP = env.float("ASSISTANT_RERANK_AMBIGUITY_GAP", default=0.004)

# Per-task-class SDK timeout ceiling, in seconds (ai-reliability T2.2). Keys are the ``feature``
# label callers already pass to gateway.complete_json/complete_stream — the task-class enum from
# Docs/plan/ai-reliability-roadmap/FILE_02 (T2.3/T2.4 formalize routing per class; this just bounds
# how long each waits). An unlisted or missing feature falls back to the default below.
ASSISTANT_DEFAULT_TIMEOUT_S = env.int("ASSISTANT_DEFAULT_TIMEOUT_S", default=60)
ASSISTANT_TASK_TIMEOUTS = {
    "chat": 60,
    "agent_plan": 60,
    "agent_answer": 60,
    "ask": 60,
    "extract": 90,
    "digest": 120,
    "suggest": 30,
    "judge": 30,
    "eval": 30,
    "embed": 10,
    "rerank": 10,
}

# Exact-match response cache (ai-reliability T2.5): only these task classes may cache — the
# deterministic system tasks where identical input means an identical answer is correct.
# chat/ask/agent_*/extract are hard-denied in gateway/cache.py regardless of this set. TTLs are
# seconds; None (or an unlisted task) = no expiry — a judge grade of a fixed transcript never
# goes stale, only a cache.bump("judge") invalidates it.
ASSISTANT_CACHE_TASKS = {"digest", "suggest", "judge", "rerank"}
ASSISTANT_CACHE_TTLS = {"digest": 20 * 3600, "suggest": 6 * 3600, "judge": None, "rerank": 6 * 3600}

# Semantic cache for knowledge Q&A (ai-reliability T2.8): a near-duplicate question (cosine ≥
# threshold, same user, current knowledge version) reuses a verified answer instead of re-running
# the router + answer model. Independent of the exact-match cache above (gateway/cache.py). Kill
# switch defaults ON in dev; cap is rows kept per user, oldest evicted first.
ASSISTANT_SEMANTIC_CACHE = env.bool("ASSISTANT_SEMANTIC_CACHE", default=True)
ASSISTANT_SEMANTIC_CACHE_THRESHOLD = 0.95
ASSISTANT_SEMANTIC_CACHE_CAP = 500

# Token & cost budget defaults (ai-reliability T2.7), seeded into the ``assistant_budget`` table by
# migration 0006 — protect against runaway spend, not against normal usage (a customer can raise
# these; the migration only sets the day-one row). Values are microcents (same discipline as
# ``Trace.cost_microcents`` / ``money.ts``). Phase 1 measured ~290 microcents/interaction avg on
# eval-run traffic (BASELINE.md) — no real customer traffic exists pre-launch, so "10x observed
# baseline" below is applied to a generous assumed heavy-usage volume, not a precise multiplier of
# real production numbers:
#   request: ~10x the worst realistic single call (ASSISTANT_MAX_TOKENS output on the most
#            expensive priced model, plus a generous input allowance).
#   user/day: ~10x a heavy user's Phase-1-rate day (200 interactions/day).
#   org/month: ~10x a 20-user shop's Phase-1-rate month.
ASSISTANT_BUDGET_REQUEST_MICROCENTS = env.int("ASSISTANT_BUDGET_REQUEST_MICROCENTS", default=50_000)
ASSISTANT_BUDGET_USER_DAY_MICROCENTS = env.int("ASSISTANT_BUDGET_USER_DAY_MICROCENTS", default=500_000)
ASSISTANT_BUDGET_ORG_MONTH_MICROCENTS = env.int(
    "ASSISTANT_BUDGET_ORG_MONTH_MICROCENTS", default=300_000_000)
ASSISTANT_BUDGET_ACTION_DEFAULT = env("ASSISTANT_BUDGET_ACTION_DEFAULT", default="block")

# Per-task-class failover chain (ai-reliability T2.3), ``{task: ["provider:model", ...fallbacks]}``.
# v1: every task gets the SAME chain — today's default model first, then the other two providers'
# nearest-capability model (all four are general-purpose vision-capable chat models). ``core.py``
# doesn't consume this table yet (it still walks ``client.provider_chain()`` filtered to configured
# keys) — it exists so the breaker/trace layer has a documented, per-task chain to point at, and so
# T2.4's promotion rule below has somewhere to land a change once one clears it.
# ``embed``/``rerank`` are excluded: ``embed_text`` is Gemini-only today (no failover chain — see
# ``gateway/core.py``'s note on that seam).
_ASSISTANT_CHAIN = [
    "anthropic:claude-opus-4-8",
    "gemini:gemini-2.5-flash",
    "mistral:mistral-small-latest",
    "groq:meta-llama/llama-4-scout-17b-16e-instruct",
]
# Promotion rule (ai-reliability T2.4, enforced by evals/routing_report.promotion_verdict): a
# candidate may replace a task's primary only if its golden-set pass rate is within 2 points of the
# current primary's AND its estimated cost/case is <= 60% of the current primary's — proven via
# `manage.py eval_routing --task <task> --candidate <provider:model> --yes-live` (omit --yes-live to
# score the baseline offline first; it never spends). Routing table changes are commits, reviewed
# like any other, never a runtime toggle. Per-line status below:
ASSISTANT_ROUTING = {
    # "chat" isn't a golden-dataset feature (ask.py's streaming prose turn is covered indirectly by
    # the "ask" eval below) — no eval file to justify moving it off the strongest model yet.
    "chat": list(_ASSISTANT_CHAIN),
    # agent.py's complete_json/complete_stream calls don't pass feature= yet (pre-existing gap,
    # tracked separately — those calls are untraced today), so there's no live routing decision to
    # make until that's wired. The golden dataset's "agent" cases are eval_routing-ready
    # (`--task agent_plan`/`--task agent_answer` both map to them) once it is.
    "agent_plan": list(_ASSISTANT_CHAIN),
    "agent_answer": list(_ASSISTANT_CHAIN),
    # Offline baseline scored (T2.4): pass_rate 71.5%, ~1023 microcents/case over 123 cases — see
    # evals/results/routing_ask_groq_meta-llama_llama-4-scout-17b-16e-instruct.json. No candidate
    # has been scored live yet, so it stays on the strongest model until one clears the rule above.
    "ask": list(_ASSISTANT_CHAIN),
    # Deliberately not a T2.4 candidate — stays on the strongest model per the roadmap; extraction
    # accuracy work is Phase 5 territory, not an eval-gated cost cut.
    "extract": list(_ASSISTANT_CHAIN),
    # No call site passes feature="digest" to the gateway yet — nothing to score until one does.
    "digest": list(_ASSISTANT_CHAIN),
    # Golden cases exist (6) but no Python service backs this feature yet (see evals/runner.py's
    # "no offline runner" note) — eval_routing can't even score a baseline until one does.
    "suggest": list(_ASSISTANT_CHAIN),
    # Unused by any call site — the real judge grader (evals/graders.py's
    # `_default_judge_call`) hardcodes its own cheap cross-provider order (gemini, groq) rather
    # than reading this table.
    "judge": list(_ASSISTANT_CHAIN),
    # Used only by `manage.py calibrate_judge`'s live judge calls (feature="eval") — a calibration
    # accuracy question, not a cost-routing decision.
    "eval": list(_ASSISTANT_CHAIN),
}

# --- Workflow egress (SSRF guard) ---
# Optional host-suffix allowlist for workflow REST/webhook nodes. Empty = any PUBLIC host (private/
# loopback/link-local/metadata addresses are always blocked; see erp.workflow.adapters.egress).
WORKFLOW_EGRESS_ALLOWLIST = env.list("WORKFLOW_EGRESS_ALLOWLIST", default=[])

# --- CORS (frontend dev server) ---
CORS_ALLOWED_ORIGINS = [
    f"http://localhost:{env('WEB_PORT', default='5173')}",
    f"http://127.0.0.1:{env('WEB_PORT', default='5173')}",
]

# --- Smart Import Engine: per-entity defaults used when a row omits an optional field ---
# (FILE_05 Task B). Keys are registry entity names; each inner dict's keys are FieldSpec names.
IMPORTS_DEFAULTS: dict[str, dict] = {
    "items": {"uom": "unit"},
    "contacts": {"source": "other"},
    "sales_invoices": {"currency": "EGP"},
    "purchase_invoices": {"currency": "EGP"},
    # FILE_16: the suspense account an out-of-balance opening-balance import proposes a correcting
    # line to (3100 Retained Earnings — the conventional opening-balance-equity offset). Never
    # inserted without explicit human approval; see ``imports/adapters/accounting.py``.
    "account_opening": {"suspense_account": "3100"},
    # sub-project 2 (DESIGN_PENDING_PAYMENTS_AND_STOCK.md): a dedicated opening-suspense account for
    # item-level opening stock, distinct from GRNI (2150) and from account_opening's 3100 so the two
    # opening flows stay separately traceable; see ``erp/inventory/services/pending_stock.py``.
    "inventory_opening": {"suspense_account": "3110"},
}
# Upload size ceiling for the Smart Import Engine (FILE_11 Task C) — bigger than the plain-CSV
# `erp.core.import_api.MAX_UPLOAD_BYTES` (5 MB) since this engine targets messy, wide workbooks.
IMPORTS_MAX_FILE_MB = env.int("IMPORTS_MAX_FILE_MB", default=50)

# --- Logging: structured JSON only (no unstructured text logs) ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "erp.core.logging.JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}
