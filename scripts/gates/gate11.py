"""Gate 11 — Notifications & integration adapters.

Asserts:
- the notifications test suite passes — a domain event (sales OrderInvoiced / CRM TicketEscalated)
  triggers a channel adapter **through the single adapter interface**, every dispatch leaves exactly
  one log row, and an adapter failure is recorded + isolated from the publisher (bus isolation);
- the API is mounted and the app is installed;
- module boundary: notifications is driven by the published event **names** and must NOT import the
  sales/CRM domain/models/services internals;
- the dispatch service talks only to the adapter interface (get_adapter().send) — channels are
  swappable, not hard-coded; email goes through Django's email framework (offline-safe backend),
  the WhatsApp stub does no network;
- no raw SQL; the React notifications screen exists and is wired as its own top-level section.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
NTF = REPO_ROOT / "erp" / "notifications"
WEB_SRC = REPO_ROOT / "apps" / "web" / "src"

NOTIFICATION_TESTS = ["erp/notifications/tests"]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def check() -> None:
    # 1. Acceptance suite.
    result = subprocess.run(
        [sys.executable, "-m", "pytest", *NOTIFICATION_TESTS, "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(
            "Phase 8 notifications tests failed:\n" + result.stdout[-2500:] + "\n" + result.stderr[-1000:]
        )

    # 2. API mounted + app registered.
    _assert("erp.notifications.api.urls" in _read("config/urls.py"), "notifications API not mounted")
    _assert("erp.notifications" in _read("config/settings/base.py"), "notifications app not installed")

    # 3. Decoupling: react to the published event NAMES; never reach into the publishers' internals.
    handlers_src = _read("erp/notifications/handlers.py")
    _assert("ORDER_INVOICED" in handlers_src, "must subscribe to the sales OrderInvoiced event")
    _assert("TICKET_ESCALATED" in handlers_src, "must subscribe to the CRM TicketEscalated event")
    for forbidden in (
        "erp.sales.domain", "erp.sales.models", "erp.sales.services",
        "erp.crm.domain", "erp.crm.models", "erp.crm.services",
    ):
        for path in NTF.rglob("*.py"):
            if "/tests/" in path.as_posix() or "/migrations/" in path.as_posix():
                continue
            _assert(forbidden not in path.read_text(encoding="utf-8"),
                    f"notifications reaches past the event into {forbidden}")

    # 4. One adapter interface; dispatch is channel-agnostic and routes through it.
    base_src = _read("erp/notifications/adapters/base.py")
    for sym in ("class NotificationAdapter", "def get_adapter", "def register_adapter"):
        _assert(sym in base_src, f"adapter interface missing {sym}")
    dispatch_src = _read("erp/notifications/services/dispatch.py")
    _assert("get_adapter(" in dispatch_src, "dispatch must resolve the channel through get_adapter")
    _assert(".send(" in dispatch_src, "dispatch must call the adapter's send() interface method")
    _assert("NotificationStatus.FAILED" in dispatch_src, "dispatch must record failed sends")
    _assert("except Exception" in dispatch_src, "dispatch must isolate adapter failures")
    # Channels are swappable, not hard-coded into dispatch.
    for hardcoded in ("smtplib", "import requests"):
        _assert(hardcoded not in dispatch_src, f"dispatch must not hard-code a transport ({hardcoded})")
    adapters_init = _read("erp/notifications/adapters/__init__.py")
    _assert("EmailAdapter" in adapters_init and "WhatsAppAdapter" in adapters_init,
            "email + whatsapp adapters must be registered")

    # 5. Email is offline-safe (goes through Django's framework, backend-configurable); whatsapp stub
    #    does no network.
    email_src = _read("erp/notifications/adapters/email.py")
    _assert("send_mail" in email_src, "email adapter must send through Django's email framework")
    _assert("smtplib" not in email_src, "email adapter must not hard-code SMTP (use EMAIL_BACKEND)")
    _assert("EMAIL_BACKEND" in _read("config/settings/base.py"), "EMAIL_BACKEND not configured")
    whatsapp_src = _read("erp/notifications/adapters/whatsapp.py")
    for net in ("import requests", "urllib", "http://", "https://"):
        _assert(net not in whatsapp_src, f"whatsapp stub must be offline (found {net})")

    # 6. No raw SQL.
    for path in NTF.rglob("*.py"):
        if "/tests/" in path.as_posix() or "/migrations/" in path.as_posix():
            continue
        src = path.read_text(encoding="utf-8")
        for banned in (".raw(", "cursor.execute(", "RunSQL"):
            _assert(banned not in src, f"{path.name} uses raw SQL ({banned})")

    # 7. React screen exists + wired as its own top-level section.
    _assert((WEB_SRC / "api" / "notifications.ts").is_file(), "missing src/api/notifications.ts")
    _assert((WEB_SRC / "pages" / "notifications" / "NotificationsPage.tsx").is_file(),
            "missing pages/notifications/NotificationsPage.tsx")
    _assert((WEB_SRC / "pages" / "notifications" / "NotificationsNav.tsx").is_file(),
            "missing pages/notifications/NotificationsNav.tsx")
    app = (WEB_SRC / "App.tsx").read_text(encoding="utf-8")
    _assert('path="/notifications"' in app, "App.tsx missing the /notifications route")
    sidebar = (WEB_SRC / "app" / "Sidebar.tsx").read_text(encoding="utf-8")
    _assert('to: "/notifications"' in sidebar, "Sidebar missing the top-level notifications section")
    page = (WEB_SRC / "pages" / "notifications" / "NotificationsPage.tsx").read_text(encoding="utf-8")
    for fn in ("listNotifications", "resendNotification"):
        _assert(fn in page, f"notifications screen missing {fn}")
