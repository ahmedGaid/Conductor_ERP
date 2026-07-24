# Draft Recovery — Project 1 (WorkSession Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable, server-authoritative draft-recovery capability (`WorkSession`) and wire it into the five originally-listed workflows — create customer, create item, create sales order, create purchase order, and Smart Import — so unfinished work survives navigation, tab-close, crash, and restart.

**Architecture:** A new module-agnostic Django app `erp/worksessions/` owns a `WorkSession` table and a draft-only service that **never writes a business model**. A React hook `useDraftRecovery` autosaves the current form (debounced 800 ms idle / 5 s max-wait), flushes on unload via `fetch(keepalive:true)`, mirrors to `localStorage` as an offline backstop, and offers a calm recovery banner on return. Smart Import reuses its existing durable `ImportBatch`; the `WorkSession` there is only a pointer.

**Tech Stack:** Django + DRF (backend), React 18 + TypeScript + Vite + react-i18next (frontend), pytest (backend tests), Vitest (frontend pure-logic tests).

**Spec:** `docs/superpowers/specs/2026-07-24-draft-recovery-design.md` (§4 backend, §5 frontend, §5.4 wiring).

## Global Constraints

Copied verbatim from the spec / project working agreement — every task's requirements include these:

- **Draft ≠ business transaction.** The `worksessions` service reads/writes only `WorkSession`. Never create or mutate a customer/item/order/journal to represent draft progress. Real writes stay in the owning module's existing service contract (`erp.sales.contracts.create_customer`, `erp.inventory.contracts.create_item`, `createOrder`, `createPurchaseOrder`).
- **RBAC / privacy.** Draft API is `IsAuthenticated`; every view owner-scopes through `_get_owned_session` — a user can never read or mutate another user's draft (404 for missing, 403 for not-owned).
- **i18n ar/en parity is build-blocking.** Every user-facing string is a key in BOTH `apps/web/src/i18n/locales/ar.json` and `en.json`. No hardcoded strings.
- **Tokens only / logical CSS only.** Raw hex lives ONLY in `tokens.css`; elsewhere `var(--color-*)`. Use `inline-start/end`, `block-*`, `text-align: start/end` — never physical `left/right`. RTL is the default.
- **No new dependencies.** Reuse existing primitives (`apiFetch`, `getToken`, `relativeTime`, `btn`/`btn--sm`/`btn--ghost`/`btn--primary`, `sysbanner` visual language).
- **Money:** integer minor units on the wire; format/parse only at the edge (`lib/money.ts`). (Draft payloads store whatever the form already holds — strings for the create forms.)
- **Before "done" (frontend):** from `apps/web` run `node scripts/check-i18n-parity.mjs`, `npx tsc --noEmit`, `npm run test`; from repo root `python scripts/gates/gate03.py`.
- **Before "done" (backend):** from repo root `python -m pytest erp/worksessions/tests -q`.
- **Module scaffolding matches `erp/imports/`** (flat `models.py`, `api/views.py`, `api/urls.py`, `tests/`), NOT the `domain/models.py` layout of business modules.

---

## File Structure

**Backend — new app `erp/worksessions/`:**
- `erp/worksessions/__init__.py` — empty package marker.
- `erp/worksessions/apps.py` — `WorkSessionsConfig` app config.
- `erp/worksessions/models.py` — `WorkSession` model (one responsibility: the draft table).
- `erp/worksessions/services.py` — draft bookkeeping (`upsert_draft`/`get_active`/`list_active`/`complete`/`discard` + `UpsertResult`). Never touches business models.
- `erp/worksessions/api/__init__.py`
- `erp/worksessions/api/serializers.py` — `serialize_session` (read shape for the client).
- `erp/worksessions/api/views.py` — `_envelope`, `_get_owned_session`, the five views.
- `erp/worksessions/api/urls.py` — routes.
- `erp/worksessions/migrations/__init__.py` + generated `0001_initial.py`.
- `erp/worksessions/tests/__init__.py`, `tests/test_service.py`, `tests/test_api.py`.
- **Modify** `config/settings/base.py` — add `"erp.worksessions"` to `LOCAL_APPS`.
- **Modify** `config/urls.py` — mount `path("api/worksessions/", include("erp.worksessions.api.urls"))`.

**Frontend — `apps/web/src/`:**
- `lib/draftRecovery.ts` — pure decisions (`isMeaningfulChange`, `reconcile`, `hasConflict`).
- `lib/draftRecovery.test.ts` — Vitest units.
- `api/workSessions.ts` — typed client + `flushDraft` (keepalive).
- `hooks/useDraftRecovery.ts` — the hook.
- `components/DraftRecoveryBanner.tsx` + `components/DraftRecoveryBanner.css`.
- `components/DraftStatusIndicator.tsx` + `components/DraftStatusIndicator.css`.
- `pages/drafts/DraftsPage.tsx` + `pages/drafts/drafts.css`.
- **Modify** `apps/web/src/App.tsx` — add the `/drafts` route.
- **Modify** `apps/web/src/i18n/locales/en.json` + `ar.json` — the `drafts.*` keys.
- **Modify (wiring)** `pages/sales/CustomersPage.tsx`, `pages/inventory/ItemsPage.tsx`, `pages/sales/NewOrderPage.tsx`, `pages/purchasing/NewPurchaseOrderPage.tsx`, `pages/imports/UploadStep.tsx` (+ `ImportWizard.tsx` if needed).

---

## Task 1: WorkSession model + app scaffold + migration

**Files:**
- Create: `erp/worksessions/__init__.py`, `erp/worksessions/apps.py`, `erp/worksessions/models.py`, `erp/worksessions/migrations/__init__.py`
- Modify: `config/settings/base.py:53-71` (LOCAL_APPS)
- Test: (migration + registration verified by `manage.py check` / makemigrations; model behavior tested in Task 2)

**Interfaces:**
- Produces: `erp.worksessions.models.WorkSession` with fields `owner` (FK user), `workflow_key: str`, `entity_type: str`, `related_entity_id: str`, `status` (`WorkSession.Status`: `ACTIVE`/`COMPLETED`/`DISCARDED`/`SUPERSEDED`), `payload: dict`, `schema_version: int`, `client_version: int`, `last_active_at: datetime`, `import_batch` (FK `imports.ImportBatch`, nullable), plus inherited `id` (uuid), `created_at`, `updated_at`. Partial-unique on `(owner, workflow_key, related_entity_id)` where `status="active"`.

- [ ] **Step 1: Create the package marker**

Create `erp/worksessions/__init__.py` (empty file).

- [ ] **Step 2: Create the app config**

Create `erp/worksessions/apps.py`:

```python
from django.apps import AppConfig


class WorkSessionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "erp.worksessions"
    label = "worksessions"
```

- [ ] **Step 3: Create the migrations package**

Create `erp/worksessions/migrations/__init__.py` (empty file).

- [ ] **Step 4: Write the model**

Create `erp/worksessions/models.py`:

```python
"""Persistent work-in-progress (draft) sessions — a module-agnostic platform capability.

A WorkSession preserves the *unsaved* state of a form or wizard so the user can leave and return to
exactly where they were. It is deliberately NOT a business record: this module never writes a
customer/order/journal — completion just flips a status, and the real write goes through the owning
module's own service contract. See docs/superpowers/specs/2026-07-24-draft-recovery-design.md.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from erp.core.models import TimeStampedModel


class WorkSession(TimeStampedModel):
    """One user's in-progress draft for a single form/wizard (uuid pk + created/updated from base)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "active"
        COMPLETED = "completed", "completed"
        DISCARDED = "discarded", "discarded"
        SUPERSEDED = "superseded", "superseded"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="work_sessions",
    )
    workflow_key = models.CharField(max_length=64)  # e.g. "sales.customer.create"
    entity_type = models.CharField(max_length=64, blank=True, default="")
    related_entity_id = models.CharField(max_length=64, blank=True, default="")  # "" for a create draft
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    payload = models.JSONField(default=dict)  # the form draft: field values + current step
    schema_version = models.PositiveIntegerField(default=1)  # bump when a form's payload shape changes
    client_version = models.PositiveIntegerField(default=0)  # monotonic; drives conflict detection
    last_active_at = models.DateTimeField(default=timezone.now)  # touched on each content save
    import_batch = models.ForeignKey(
        "imports.ImportBatch", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        db_table = "worksessions_session"
        ordering = ["-last_active_at"]
        indexes = [
            models.Index(fields=["owner", "workflow_key", "status"]),
            models.Index(fields=["owner", "status", "last_active_at"]),
        ]
        constraints = [
            # At most one ACTIVE draft per form per user → no duplicate drafts.
            models.UniqueConstraint(
                fields=["owner", "workflow_key", "related_entity_id"],
                condition=models.Q(status="active"),
                name="uniq_active_worksession_per_form",
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.workflow_key} draft for owner={self.owner_id} ({self.status})"
```

- [ ] **Step 5: Register the app**

In `config/settings/base.py`, add `"erp.worksessions"` to the end of the `LOCAL_APPS` list (after `"erp.imports",`):

```python
LOCAL_APPS = [
    # ... existing entries ...
    "erp.imports",
    "erp.worksessions",
]
```

- [ ] **Step 6: Generate the migration**

Run: `python manage.py makemigrations worksessions`
Expected: creates `erp/worksessions/migrations/0001_initial.py` with the `WorkSession` model, indexes, and the partial `UniqueConstraint`.

- [ ] **Step 7: Verify the project still checks + migrates**

Run: `python manage.py migrate worksessions`
Expected: applies `0001_initial` with no error.
Run: `python manage.py check`
Expected: `System check identified no issues`.

- [ ] **Step 8: Commit**

```bash
git add erp/worksessions/__init__.py erp/worksessions/apps.py erp/worksessions/models.py erp/worksessions/migrations config/settings/base.py
git commit -m "feat(worksessions): add WorkSession draft model + app scaffold"
```

---

## Task 2: WorkSession service + tests

**Files:**
- Create: `erp/worksessions/services.py`
- Create: `erp/worksessions/tests/__init__.py`, `erp/worksessions/tests/test_service.py`

**Interfaces:**
- Consumes: `WorkSession` (Task 1).
- Produces:
  - `UpsertResult(session: WorkSession, conflict: bool)` (frozen dataclass).
  - `get_active(owner, workflow_key: str, related_entity_id: str = "") -> WorkSession | None`
  - `list_active(owner) -> list[WorkSession]`
  - `upsert_draft(owner, *, workflow_key, payload, entity_type="", related_entity_id="", schema_version=1, client_version=0, expected_version=None, import_batch=None) -> UpsertResult`
  - `complete(owner, session_id, *, related_entity_id="") -> None`
  - `discard(owner, session_id) -> None`

- [ ] **Step 1: Create the tests package marker**

Create `erp/worksessions/tests/__init__.py` (empty file).

- [ ] **Step 2: Write the failing service tests**

Create `erp/worksessions/tests/test_service.py`:

```python
import pytest
from django.contrib.auth import get_user_model

from erp.worksessions import services
from erp.worksessions.models import WorkSession

User = get_user_model()
pytestmark = pytest.mark.django_db


def _user(username="u1"):
    return User.objects.create_user(username=username, password="x")


def test_upsert_creates_then_updates_the_single_active_draft():
    user = _user()
    r1 = services.upsert_draft(user, workflow_key="sales.customer.create", payload={"name": "A"}, schema_version=1)
    assert r1.conflict is False
    assert r1.session.client_version == 1
    r2 = services.upsert_draft(
        user, workflow_key="sales.customer.create", payload={"name": "AB"},
        schema_version=1, expected_version=r1.session.client_version,
    )
    assert r2.session.id == r1.session.id  # same row, not a duplicate
    assert r2.session.payload == {"name": "AB"}
    assert r2.session.client_version == 2
    assert WorkSession.objects.filter(owner=user, status=WorkSession.Status.ACTIVE).count() == 1


def test_get_active_returns_only_the_owners_active_draft():
    a, b = _user("a"), _user("b")
    services.upsert_draft(a, workflow_key="sales.customer.create", payload={"name": "A"})
    assert services.get_active(a, "sales.customer.create") is not None
    assert services.get_active(b, "sales.customer.create") is None  # owner-scoped


def test_stale_expected_version_reports_conflict_without_clobbering():
    user = _user()
    r1 = services.upsert_draft(user, workflow_key="k", payload={"v": 1})   # client_version 1
    services.upsert_draft(user, workflow_key="k", payload={"v": 2}, expected_version=1)  # -> 2
    # A second client still thinks the version is 1 → conflict, and the stored payload is untouched.
    res = services.upsert_draft(user, workflow_key="k", payload={"v": 99}, expected_version=1)
    assert res.conflict is True
    res.session.refresh_from_db()
    assert res.session.payload == {"v": 2}


def test_complete_and_discard_free_the_active_slot():
    user = _user()
    r = services.upsert_draft(user, workflow_key="k", payload={"v": 1})
    services.complete(user, r.session.id, related_entity_id="C-001")
    r.session.refresh_from_db()
    assert r.session.status == WorkSession.Status.COMPLETED
    assert r.session.related_entity_id == "C-001"
    # The active slot is now free → a new active draft can be created for the same form.
    r2 = services.upsert_draft(user, workflow_key="k", payload={"v": 2})
    assert r2.session.id != r.session.id
    services.discard(user, r2.session.id)
    r2.session.refresh_from_db()
    assert r2.session.status == WorkSession.Status.DISCARDED


def test_complete_and_discard_ignore_another_users_session():
    a, b = _user("a"), _user("b")
    r = services.upsert_draft(a, workflow_key="k", payload={"v": 1})
    services.discard(b, r.session.id)  # b is not the owner → no-op
    r.session.refresh_from_db()
    assert r.session.status == WorkSession.Status.ACTIVE


def test_list_active_is_owner_scoped_and_newest_first():
    a = _user("a")
    services.upsert_draft(a, workflow_key="k1", payload={"v": 1})
    services.upsert_draft(a, workflow_key="k2", payload={"v": 1})
    keys = [s.workflow_key for s in services.list_active(a)]
    assert set(keys) == {"k1", "k2"}
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `python -m pytest erp/worksessions/tests/test_service.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'erp.worksessions.services'`.

- [ ] **Step 4: Write the service**

Create `erp/worksessions/services.py`:

```python
"""WorkSession service — draft bookkeeping only. NEVER writes a business model.

Every function is owner-scoped: a caller can only see or mutate its own drafts. Completion flips a
status; the real business write happens in the owning module's service contract, untouched.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import WorkSession


@dataclass(frozen=True)
class UpsertResult:
    session: WorkSession
    conflict: bool


def get_active(owner, workflow_key: str, related_entity_id: str = "") -> WorkSession | None:
    return WorkSession.objects.filter(
        owner=owner, workflow_key=workflow_key, related_entity_id=related_entity_id,
        status=WorkSession.Status.ACTIVE,
    ).first()


def list_active(owner) -> list[WorkSession]:
    return list(
        WorkSession.objects.filter(owner=owner, status=WorkSession.Status.ACTIVE)
        .order_by("-last_active_at")
    )


@transaction.atomic
def upsert_draft(
    owner, *, workflow_key: str, payload: dict, entity_type: str = "",
    related_entity_id: str = "", schema_version: int = 1, client_version: int = 0,
    expected_version: int | None = None, import_batch=None,
) -> UpsertResult:
    """Create or update the single ACTIVE draft for (owner, workflow_key, related_entity_id).

    Conflict: if ``expected_version`` is given and is < the stored ``client_version``, another writer
    moved ahead since this client last read — return ``conflict=True`` WITHOUT clobbering. The client
    decides whether to overwrite (last-write-wins) after warning the user.
    """
    existing = (
        WorkSession.objects.select_for_update()
        .filter(owner=owner, workflow_key=workflow_key, related_entity_id=related_entity_id,
                status=WorkSession.Status.ACTIVE)
        .first()
    )
    if existing is None:
        try:
            with transaction.atomic():
                session = WorkSession.objects.create(
                    owner=owner, workflow_key=workflow_key, entity_type=entity_type,
                    related_entity_id=related_entity_id, payload=payload,
                    schema_version=schema_version, client_version=max(client_version, 1),
                    last_active_at=timezone.now(), import_batch=import_batch,
                )
            return UpsertResult(session=session, conflict=False)
        except IntegrityError:
            # A concurrent create won the unique-active slot — fall through to update it.
            existing = (
                WorkSession.objects.select_for_update()
                .filter(owner=owner, workflow_key=workflow_key,
                        related_entity_id=related_entity_id, status=WorkSession.Status.ACTIVE)
                .first()
            )

    if expected_version is not None and expected_version < existing.client_version:
        return UpsertResult(session=existing, conflict=True)

    existing.payload = payload
    existing.entity_type = entity_type or existing.entity_type
    existing.schema_version = schema_version
    existing.client_version = existing.client_version + 1
    existing.last_active_at = timezone.now()
    if import_batch is not None:
        existing.import_batch = import_batch
    existing.save(update_fields=[
        "payload", "entity_type", "schema_version", "client_version",
        "last_active_at", "import_batch", "updated_at",
    ])
    return UpsertResult(session=existing, conflict=False)


def complete(owner, session_id, *, related_entity_id: str = "") -> None:
    session = WorkSession.objects.filter(owner=owner, id=session_id).first()
    if session is None:
        return  # not found or not owned — no-op
    session.status = WorkSession.Status.COMPLETED
    if related_entity_id:
        session.related_entity_id = related_entity_id
    session.save(update_fields=["status", "related_entity_id", "updated_at"])


def discard(owner, session_id) -> None:
    WorkSession.objects.filter(owner=owner, id=session_id).update(
        status=WorkSession.Status.DISCARDED
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest erp/worksessions/tests/test_service.py -q`
Expected: PASS (6 passed).

- [ ] **Step 6: Commit**

```bash
git add erp/worksessions/services.py erp/worksessions/tests
git commit -m "feat(worksessions): add owner-scoped draft service + tests"
```

---

## Task 3: WorkSession API (serializer + views + urls + mount) + tests

**Files:**
- Create: `erp/worksessions/api/__init__.py`, `erp/worksessions/api/serializers.py`, `erp/worksessions/api/views.py`, `erp/worksessions/api/urls.py`
- Create: `erp/worksessions/tests/test_api.py`
- Modify: `config/urls.py` (add the mount after the imports mount)

**Interfaces:**
- Consumes: `services` (Task 2), `WorkSession` (Task 1), `erp.core.errors` (`NotFoundError`, `PermissionError`).
- Produces (HTTP, all under `/api/worksessions/`, `{data}` envelope):
  - `GET /` → `{data: WorkSessionOut[]}` (owner's active drafts)
  - `POST /` → `{data: {session: WorkSessionOut, conflict: bool}}`
  - `GET /active?workflow_key=&related_entity_id=` → `{data: WorkSessionOut | null}`
  - `POST /<uuid:pk>/discard` → `{data: null}` (204)
  - `POST /<uuid:pk>/complete` (body `{related_entity_id?}`) → `{data: WorkSessionOut}`
  - `WorkSessionOut` = `{id, workflow_key, entity_type, related_entity_id, status, payload, schema_version, client_version, last_active_at}`.

- [ ] **Step 1: Create the api package marker**

Create `erp/worksessions/api/__init__.py` (empty file).

- [ ] **Step 2: Write the serializer**

Create `erp/worksessions/api/serializers.py`:

```python
"""Read shape for a WorkSession sent to the client. Hand-written (like other envelope views)."""
from __future__ import annotations

from ..models import WorkSession


def serialize_session(s: WorkSession) -> dict:
    return {
        "id": str(s.id),
        "workflow_key": s.workflow_key,
        "entity_type": s.entity_type,
        "related_entity_id": s.related_entity_id,
        "status": s.status,
        "payload": s.payload,
        "schema_version": s.schema_version,
        "client_version": s.client_version,
        "last_active_at": s.last_active_at.isoformat(),
    }
```

- [ ] **Step 3: Write the views**

Create `erp/worksessions/api/views.py`:

```python
"""WorkSession API — the signed-in user's private drafts. IsAuthenticated + owner-scoped."""
from __future__ import annotations

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from erp.core.errors import NotFoundError
from erp.core.errors import PermissionError as ForbiddenError

from .. import services
from ..models import WorkSession
from .serializers import serialize_session


def _envelope(data, status: int = 200) -> Response:
    return Response({"data": data}, status=status)


def _get_owned_session(actor, pk) -> WorkSession:
    try:
        session = WorkSession.objects.get(pk=pk)
    except WorkSession.DoesNotExist:
        raise NotFoundError("Draft not found.")
    if session.owner_id != actor.id:
        raise ForbiddenError("You do not have access to this draft.")
    return session


class DraftListCreateView(APIView):
    """GET — the user's active drafts (the drafts surface). POST — upsert the current form's draft."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return _envelope([serialize_session(s) for s in services.list_active(request.user)])

    def post(self, request: Request) -> Response:
        d = request.data
        result = services.upsert_draft(
            request.user,
            workflow_key=d["workflow_key"],
            payload=d.get("payload", {}),
            entity_type=d.get("entity_type", ""),
            related_entity_id=d.get("related_entity_id", ""),
            schema_version=int(d.get("schema_version", 1)),
            client_version=int(d.get("client_version", 0)),
            expected_version=(int(d["expected_version"]) if d.get("expected_version") is not None else None),
        )
        return _envelope(
            {"session": serialize_session(result.session), "conflict": result.conflict},
            status=201,
        )


class ActiveDraftView(APIView):
    """GET the single active draft for one form (or null)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        workflow_key = request.query_params.get("workflow_key", "")
        related_entity_id = request.query_params.get("related_entity_id", "")
        session = services.get_active(request.user, workflow_key, related_entity_id)
        return _envelope(serialize_session(session) if session else None)


class DiscardDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk) -> Response:
        session = _get_owned_session(request.user, pk)
        services.discard(request.user, session.id)
        return _envelope(None, status=204)


class CompleteDraftView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk) -> Response:
        session = _get_owned_session(request.user, pk)
        services.complete(
            request.user, session.id,
            related_entity_id=request.data.get("related_entity_id", ""),
        )
        session.refresh_from_db()
        return _envelope(serialize_session(session))
```

- [ ] **Step 4: Write the urls**

Create `erp/worksessions/api/urls.py`:

```python
"""WorkSession API routes."""
from django.urls import path

from . import views

app_name = "worksessions"

urlpatterns = [
    path("", views.DraftListCreateView.as_view(), name="draft-list-create"),
    path("active", views.ActiveDraftView.as_view(), name="draft-active"),
    path("<uuid:pk>/discard", views.DiscardDraftView.as_view(), name="draft-discard"),
    path("<uuid:pk>/complete", views.CompleteDraftView.as_view(), name="draft-complete"),
]
```

- [ ] **Step 5: Mount the API**

In `config/urls.py`, add the mount immediately after the imports mount (`path("api/imports/", include("erp.imports.api.urls")),`):

```python
    path("api/worksessions/", include("erp.worksessions.api.urls")),
```

- [ ] **Step 6: Write the failing API tests**

Create `erp/worksessions/tests/test_api.py`:

```python
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
pytestmark = pytest.mark.django_db


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def test_requires_authentication():
    resp = APIClient().get("/api/worksessions/active?workflow_key=k")
    assert resp.status_code in (401, 403)


def test_upsert_then_fetch_active_roundtrips():
    user = User.objects.create_user(username="u", password="x")
    c = _client(user)
    resp = c.post("/api/worksessions/", {
        "workflow_key": "sales.customer.create",
        "payload": {"name": "Acme"},
        "schema_version": 1,
        "client_version": 1,
    }, format="json")
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["conflict"] is False
    assert body["session"]["payload"] == {"name": "Acme"}

    active = c.get("/api/worksessions/active?workflow_key=sales.customer.create").json()["data"]
    assert active is not None
    assert active["payload"] == {"name": "Acme"}


def test_user_cannot_access_another_users_draft():
    a = User.objects.create_user(username="a", password="x")
    b = User.objects.create_user(username="b", password="x")
    session_id = _client(a).post("/api/worksessions/", {
        "workflow_key": "k", "payload": {"v": 1}, "schema_version": 1, "client_version": 1,
    }, format="json").json()["data"]["session"]["id"]

    resp = _client(b).post(f"/api/worksessions/{session_id}/discard", {}, format="json")
    assert resp.status_code == 403  # owner-scoped: PermissionError -> 403


def test_complete_marks_the_draft_completed():
    user = User.objects.create_user(username="u", password="x")
    c = _client(user)
    session_id = c.post("/api/worksessions/", {
        "workflow_key": "k", "payload": {"v": 1}, "schema_version": 1, "client_version": 1,
    }, format="json").json()["data"]["session"]["id"]

    done = c.post(f"/api/worksessions/{session_id}/complete", {"related_entity_id": "C-9"}, format="json")
    assert done.status_code == 200
    assert done.json()["data"]["status"] == "completed"
    # No longer offered as an active draft.
    assert c.get("/api/worksessions/active?workflow_key=k").json()["data"] is None
```

- [ ] **Step 7: Run the API tests to verify they pass**

Run: `python -m pytest erp/worksessions/tests/test_api.py -q`
Expected: PASS (4 passed). If `test_user_cannot_access_another_users_draft` returns 404 instead of 403, confirm `_get_owned_session` raises `PermissionError as ForbiddenError` (403) for a found-but-not-owned row — 403 is required.

- [ ] **Step 8: Run the whole module suite**

Run: `python -m pytest erp/worksessions/tests -q`
Expected: PASS (10 passed).

- [ ] **Step 9: Commit**

```bash
git add erp/worksessions/api erp/worksessions/tests/test_api.py config/urls.py
git commit -m "feat(worksessions): add owner-scoped draft API + tests"
```

---

## Task 4: Frontend pure logic (`lib/draftRecovery.ts`) + Vitest

**Files:**
- Create: `apps/web/src/lib/draftRecovery.ts`
- Test: `apps/web/src/lib/draftRecovery.test.ts`

**Interfaces:**
- Produces:
  - `isMeaningfulChange<T>(current: T, baseline: T): boolean`
  - `Candidate<T> = { payload: T; clientVersion: number }`
  - `reconcile<T>(server: Candidate<T> | null, local: Candidate<T> | null): { source: "server" | "local" | "none"; payload: T | null }`
  - `hasConflict(expectedVersion: number, storedVersion: number): boolean`

- [ ] **Step 1: Write the failing tests**

Create `apps/web/src/lib/draftRecovery.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { isMeaningfulChange, reconcile, hasConflict } from "./draftRecovery";

describe("isMeaningfulChange", () => {
  it("is false when the value equals the empty baseline", () => {
    expect(isMeaningfulChange({ name: "" }, { name: "" })).toBe(false);
  });
  it("is true once any field differs from the baseline", () => {
    expect(isMeaningfulChange({ name: "A" }, { name: "" })).toBe(true);
  });
});

describe("reconcile", () => {
  const s = { payload: { v: "server" }, clientVersion: 2 };
  const l = { payload: { v: "local" }, clientVersion: 3 };
  it("returns none when both are absent", () => {
    expect(reconcile(null, null)).toEqual({ source: "none", payload: null });
  });
  it("prefers the only side present", () => {
    expect(reconcile(s, null).source).toBe("server");
    expect(reconcile(null, l).source).toBe("local");
  });
  it("prefers the higher clientVersion when both exist (local ahead after a mid-flight crash)", () => {
    expect(reconcile(s, l)).toEqual({ source: "local", payload: { v: "local" } });
  });
  it("prefers the server when it is at least as new", () => {
    expect(reconcile({ payload: { v: "server" }, clientVersion: 5 }, l).source).toBe("server");
  });
});

describe("hasConflict", () => {
  it("is true when this client's expected version trails the stored version", () => {
    expect(hasConflict(1, 2)).toBe(true);
  });
  it("is false when up to date", () => {
    expect(hasConflict(2, 2)).toBe(false);
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run (from `apps/web`): `npx vitest run src/lib/draftRecovery.test.ts`
Expected: FAIL — cannot resolve `./draftRecovery`.

- [ ] **Step 3: Write the implementation**

Create `apps/web/src/lib/draftRecovery.ts`:

```typescript
// Pure, framework-free decisions behind useDraftRecovery — unit-tested in draftRecovery.test.ts.
// Keeping them here (no React, no fetch, no timers) makes the recovery rules testable in isolation.

/** A form value is "meaningful" (worth saving/offering) when it differs from the empty baseline. */
export function isMeaningfulChange<T>(current: T, baseline: T): boolean {
  return JSON.stringify(current) !== JSON.stringify(baseline);
}

export interface Candidate<T> {
  payload: T;
  clientVersion: number;
}

/**
 * On mount, choose which stored copy to offer for recovery. The higher clientVersion wins: a crash
 * that lands after a localStorage mirror but before the server ack leaves the local copy ahead.
 */
export function reconcile<T>(
  server: Candidate<T> | null,
  local: Candidate<T> | null,
): { source: "server" | "local" | "none"; payload: T | null } {
  if (!server && !local) return { source: "none", payload: null };
  if (server && !local) return { source: "server", payload: server.payload };
  if (local && !server) return { source: "local", payload: local.payload };
  if (local!.clientVersion > server!.clientVersion) return { source: "local", payload: local!.payload };
  return { source: "server", payload: server!.payload };
}

/** True when the stored draft has advanced past what this client last saw — a conflicting write. */
export function hasConflict(expectedVersion: number, storedVersion: number): boolean {
  return expectedVersion < storedVersion;
}
```

- [ ] **Step 4: Run to verify it passes**

Run (from `apps/web`): `npx vitest run src/lib/draftRecovery.test.ts`
Expected: PASS (all cases green).

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/lib/draftRecovery.ts apps/web/src/lib/draftRecovery.test.ts
git commit -m "feat(web): add pure draft-recovery decision logic + unit tests"
```

---

## Task 5: Frontend API client (`api/workSessions.ts`)

**Files:**
- Create: `apps/web/src/api/workSessions.ts`

**Interfaces:**
- Consumes: `apiFetch`, `getToken` from `./client`.
- Produces:
  - `WorkSessionDraft` (matches the server `WorkSessionOut`).
  - `DraftSaveBody = { workflow_key; payload; entity_type?; related_entity_id?; schema_version; client_version; expected_version? }`
  - `getActiveDraft(workflowKey, relatedEntityId?) : Promise<WorkSessionDraft | null>`
  - `listDrafts() : Promise<WorkSessionDraft[]>`
  - `saveDraft(body: DraftSaveBody) : Promise<{ session: WorkSessionDraft; conflict: boolean }>`
  - `discardDraft(id: string) : Promise<void>`
  - `completeDraft(id: string, relatedEntityId?: string) : Promise<WorkSessionDraft>`
  - `flushDraft(body: DraftSaveBody) : void` (unload; `fetch(keepalive:true)` with the bearer header)

- [ ] **Step 1: Write the client**

Create `apps/web/src/api/workSessions.ts`:

```typescript
// Typed client for the WorkSession draft API (/api/worksessions/*). Drafts are private to the user.
import { apiFetch, getToken } from "./client";

export type DraftStatus = "active" | "completed" | "discarded" | "superseded";

export interface WorkSessionDraft {
  id: string;
  workflow_key: string;
  entity_type: string;
  related_entity_id: string;
  status: DraftStatus;
  payload: unknown;
  schema_version: number;
  client_version: number;
  last_active_at: string;
}

export interface DraftSaveBody {
  workflow_key: string;
  payload: unknown;
  entity_type?: string;
  related_entity_id?: string;
  schema_version: number;
  client_version: number;
  expected_version?: number | null;
}

export function getActiveDraft(
  workflowKey: string,
  relatedEntityId = "",
): Promise<WorkSessionDraft | null> {
  const params = new URLSearchParams({ workflow_key: workflowKey });
  if (relatedEntityId) params.set("related_entity_id", relatedEntityId);
  return apiFetch<WorkSessionDraft | null>(`/worksessions/active?${params.toString()}`);
}

export function listDrafts(): Promise<WorkSessionDraft[]> {
  return apiFetch<WorkSessionDraft[]>("/worksessions/");
}

export function saveDraft(
  body: DraftSaveBody,
): Promise<{ session: WorkSessionDraft; conflict: boolean }> {
  return apiFetch("/worksessions/", { method: "POST", body: JSON.stringify(body) });
}

export function discardDraft(id: string): Promise<void> {
  return apiFetch(`/worksessions/${id}/discard`, { method: "POST", body: "{}" });
}

export function completeDraft(id: string, relatedEntityId = ""): Promise<WorkSessionDraft> {
  return apiFetch(`/worksessions/${id}/complete`, {
    method: "POST",
    body: JSON.stringify({ related_entity_id: relatedEntityId }),
  });
}

/**
 * Best-effort flush used on page hide/unload. `fetch(keepalive:true)` outlives the page AND carries
 * the in-memory JWT `Authorization` header (which `navigator.sendBeacon` cannot set, so a beacon
 * would post unauthenticated). Body is far under keepalive's 64 KB cap. Response is ignored.
 */
export function flushDraft(body: DraftSaveBody): void {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    void fetch("/api/worksessions/", {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      keepalive: true,
    });
  } catch {
    /* best-effort on unload — nothing else we can do */
  }
}
```

- [ ] **Step 2: Type-check**

Run (from `apps/web`): `npx tsc --noEmit`
Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/api/workSessions.ts
git commit -m "feat(web): add WorkSession draft API client + keepalive flush"
```

---

## Task 6: The `useDraftRecovery` hook

**Files:**
- Create: `apps/web/src/hooks/useDraftRecovery.ts`

**Interfaces:**
- Consumes: Task 4 (`isMeaningfulChange`, `reconcile`, `hasConflict`), Task 5 (client fns + types).
- Produces: `useDraftRecovery<T>(opts) => DraftRecovery<T>` where
  - `opts = { workflowKey: string; value: T; baseline: T; schemaVersion: number; relatedEntityId?: string; entityType?: string; enabled?: boolean }`
  - `DraftRecovery<T> = { status: "idle"|"saving"|"saved"; savedAt: Date | null; recoverable: { payload: T; lastActiveAt: string } | null; recover: () => T | null; discard: () => Promise<void>; complete: (relatedEntityId?: string) => Promise<void>; conflict: boolean }`

> **Note on TDD here:** the pure decisions are already unit-tested in Task 4. This hook is a thin React shell over timers, `fetch`, `localStorage`, and `window` events — verified by manual browser steps in the wiring tasks (9–13), not a Vitest unit (it would require mocking four browser subsystems for little signal). Implement it directly, then `tsc`.

- [ ] **Step 1: Write the hook**

Create `apps/web/src/hooks/useDraftRecovery.ts`:

```typescript
import { useCallback, useEffect, useRef, useState } from "react";

import {
  completeDraft,
  discardDraft,
  flushDraft,
  getActiveDraft,
  saveDraft,
  type DraftSaveBody,
} from "../api/workSessions";
import { hasConflict, isMeaningfulChange, reconcile } from "../lib/draftRecovery";

const IDLE_MS = 800;
const MAX_WAIT_MS = 5000;

function localKey(workflowKey: string, relatedEntityId: string): string {
  return `erp.draft.${workflowKey}.${relatedEntityId}`;
}

interface LocalMirror<T> {
  payload: T;
  clientVersion: number;
  savedAt: number;
}

export interface DraftRecovery<T> {
  status: "idle" | "saving" | "saved";
  savedAt: Date | null;
  recoverable: { payload: T; lastActiveAt: string } | null;
  /** Apply the offered draft: returns its payload for the page to load, and clears the banner. */
  recover: () => T | null;
  discard: () => Promise<void>;
  complete: (relatedEntityId?: string) => Promise<void>;
  conflict: boolean;
}

export function useDraftRecovery<T>(opts: {
  workflowKey: string;
  value: T;
  baseline: T;
  schemaVersion: number;
  relatedEntityId?: string;
  entityType?: string;
  enabled?: boolean;
}): DraftRecovery<T> {
  const {
    workflowKey,
    value,
    baseline,
    schemaVersion,
    relatedEntityId = "",
    entityType = "",
    enabled = true,
  } = opts;

  const [status, setStatus] = useState<"idle" | "saving" | "saved">("idle");
  const [savedAt, setSavedAt] = useState<Date | null>(null);
  const [recoverable, setRecoverable] = useState<{ payload: T; lastActiveAt: string } | null>(null);
  const [conflict, setConflict] = useState(false);

  // Bookkeeping in refs so the debounce/flush closures always read the latest.
  const sessionIdRef = useRef<string | null>(null);
  const serverVersionRef = useRef(0);
  const lastSavedJsonRef = useRef<string | null>(null);
  const valueRef = useRef(value);
  valueRef.current = value;

  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const maxTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const lsKey = localKey(workflowKey, relatedEntityId);

  function writeMirror(payload: T, clientVersion: number) {
    try {
      localStorage.setItem(lsKey, JSON.stringify({ payload, clientVersion, savedAt: Date.now() }));
    } catch {
      /* storage unavailable (private mode) */
    }
  }

  // --- mount: fetch the active draft, reconcile with the local mirror, offer recovery ---
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    let local: LocalMirror<T> | null = null;
    try {
      const raw = localStorage.getItem(lsKey);
      if (raw) local = JSON.parse(raw) as LocalMirror<T>;
    } catch {
      /* ignore */
    }

    getActiveDraft(workflowKey, relatedEntityId)
      .then((server) => {
        if (cancelled) return;
        if (server) {
          sessionIdRef.current = server.id;
          serverVersionRef.current = server.client_version;
        }
        const chosen = reconcile(
          server ? { payload: server.payload as T, clientVersion: server.client_version } : null,
          local ? { payload: local.payload, clientVersion: local.clientVersion } : null,
        );
        if (chosen.source !== "none" && chosen.payload != null && isMeaningfulChange(chosen.payload, baseline)) {
          const lastActiveAt = server?.last_active_at ?? new Date(local?.savedAt ?? Date.now()).toISOString();
          setRecoverable({ payload: chosen.payload, lastActiveAt });
        }
      })
      .catch(() => {
        // Offline: fall back to the local mirror only.
        if (cancelled || !local) return;
        if (isMeaningfulChange(local.payload, baseline)) {
          setRecoverable({ payload: local.payload, lastActiveAt: new Date(local.savedAt).toISOString() });
        }
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowKey, relatedEntityId, enabled]);

  // --- the actual save ---
  const doSave = useCallback(async () => {
    const current = valueRef.current;
    if (!isMeaningfulChange(current, baseline)) return;
    const json = JSON.stringify(current);
    if (json === lastSavedJsonRef.current) return;
    setStatus("saving");
    const body: DraftSaveBody = {
      workflow_key: workflowKey,
      payload: current,
      entity_type: entityType,
      related_entity_id: relatedEntityId,
      schema_version: schemaVersion,
      client_version: serverVersionRef.current + 1,
      expected_version: serverVersionRef.current,
    };
    try {
      const res = await saveDraft(body);
      if (res.conflict) {
        setConflict(true);
        setStatus("idle");
        return;
      }
      sessionIdRef.current = res.session.id;
      serverVersionRef.current = res.session.client_version;
      lastSavedJsonRef.current = json;
      writeMirror(current, res.session.client_version);
      setSavedAt(new Date());
      setStatus("saved");
    } catch {
      // Network failure: keep the local mirror as the backstop; stay idle so the next edit retries.
      writeMirror(current, serverVersionRef.current + 1);
      setStatus("idle");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowKey, relatedEntityId, entityType, schemaVersion, baseline, lsKey]);

  // --- debounce: idle 800 ms, max-wait 5 s ---
  useEffect(() => {
    if (!enabled) return;
    if (!isMeaningfulChange(value, baseline)) return;
    if (JSON.stringify(value) === lastSavedJsonRef.current) return;

    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => {
      if (maxTimer.current) {
        clearTimeout(maxTimer.current);
        maxTimer.current = null;
      }
      void doSave();
    }, IDLE_MS);

    if (!maxTimer.current) {
      maxTimer.current = setTimeout(() => {
        if (idleTimer.current) {
          clearTimeout(idleTimer.current);
          idleTimer.current = null;
        }
        maxTimer.current = null;
        void doSave();
      }, MAX_WAIT_MS);
    }

    return () => {
      if (idleTimer.current) clearTimeout(idleTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, enabled]);

  // --- flush on hide/unload (keepalive fetch carries the bearer header) ---
  useEffect(() => {
    if (!enabled) return;
    function flush() {
      const current = valueRef.current;
      if (!isMeaningfulChange(current, baseline)) return;
      if (JSON.stringify(current) === lastSavedJsonRef.current) return;
      flushDraft({
        workflow_key: workflowKey,
        payload: current,
        entity_type: entityType,
        related_entity_id: relatedEntityId,
        schema_version: schemaVersion,
        client_version: serverVersionRef.current + 1,
        expected_version: serverVersionRef.current,
      });
    }
    function onVisibility() {
      if (document.visibilityState === "hidden") flush();
    }
    window.addEventListener("pagehide", flush);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("pagehide", flush);
      document.removeEventListener("visibilitychange", onVisibility);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowKey, relatedEntityId, entityType, schemaVersion, enabled]);

  // --- cross-tab: a sibling tab wrote a newer version → conflict ---
  useEffect(() => {
    if (!enabled) return;
    function onStorage(e: StorageEvent) {
      if (e.key !== lsKey || !e.newValue) return;
      try {
        const mirror = JSON.parse(e.newValue) as LocalMirror<T>;
        if (hasConflict(serverVersionRef.current, mirror.clientVersion)) setConflict(true);
      } catch {
        /* ignore */
      }
    }
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lsKey, enabled]);

  const recover = useCallback((): T | null => {
    const payload = recoverable?.payload ?? null;
    setRecoverable(null);
    return payload;
  }, [recoverable]);

  const discard = useCallback(async () => {
    setRecoverable(null);
    lastSavedJsonRef.current = null;
    try {
      localStorage.removeItem(lsKey);
    } catch {
      /* ignore */
    }
    const id = sessionIdRef.current;
    if (id) {
      try {
        await discardDraft(id);
      } catch {
        /* ignore */
      }
    }
    sessionIdRef.current = null;
    serverVersionRef.current = 0;
    setStatus("idle");
    setSavedAt(null);
  }, [lsKey]);

  const complete = useCallback(
    async (rid?: string) => {
      if (idleTimer.current) clearTimeout(idleTimer.current);
      if (maxTimer.current) clearTimeout(maxTimer.current);
      try {
        localStorage.removeItem(lsKey);
      } catch {
        /* ignore */
      }
      const id = sessionIdRef.current;
      if (id) {
        try {
          await completeDraft(id, rid ?? relatedEntityId);
        } catch {
          /* ignore */
        }
      }
      sessionIdRef.current = null;
    },
    [lsKey, relatedEntityId],
  );

  return { status, savedAt, recoverable, recover, discard, complete, conflict };
}
```

- [ ] **Step 2: Type-check**

Run (from `apps/web`): `npx tsc --noEmit`
Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/hooks/useDraftRecovery.ts
git commit -m "feat(web): add useDraftRecovery hook (autosave + recovery + keepalive flush)"
```

---

## Task 7: Recovery UI components + i18n keys

**Files:**
- Create: `apps/web/src/components/DraftRecoveryBanner.tsx`, `apps/web/src/components/DraftRecoveryBanner.css`
- Create: `apps/web/src/components/DraftStatusIndicator.tsx`, `apps/web/src/components/DraftStatusIndicator.css`
- Modify: `apps/web/src/i18n/locales/en.json`, `apps/web/src/i18n/locales/ar.json`

**Interfaces:**
- Consumes: `relativeTime` from `../lib/relativeTime` (signature `relativeTime(iso, lang)`).
- Produces:
  - `DraftRecoveryBanner({ entityLabel: string; lastActiveAt: string; onContinue: () => void; onDiscard: () => void })`
  - `DraftStatusIndicator({ status: "idle"|"saving"|"saved"; savedAt: Date | null })`

- [ ] **Step 1: Add the i18n keys (English)**

In `apps/web/src/i18n/locales/en.json`, add a top-level `drafts` block (keep keys alphabetically near other top-level blocks per the file's convention):

```json
  "drafts": {
    "recovery": {
      "title": "Continue where you left off?",
      "hint": "You have an unfinished {{entity}} from {{when}}.",
      "continue": "Continue",
      "discard": "Discard"
    },
    "status": {
      "saving": "Saving…",
      "saved": "Changes saved"
    },
    "conflict": "This draft changed in another tab. Your latest edit will win when you save.",
    "page": {
      "title": "Unfinished work",
      "lede": "Drafts you started but haven't finished. Pick up where you left off, or clear them.",
      "empty": "No unfinished drafts.",
      "lastUpdated": "Last edited {{when}}",
      "continue": "Continue",
      "discard": "Discard"
    }
  },
```

- [ ] **Step 2: Add the matching i18n keys (Arabic)**

In `apps/web/src/i18n/locales/ar.json`, add the SAME key paths with Arabic values:

```json
  "drafts": {
    "recovery": {
      "title": "أكمل من حيث توقفت؟",
      "hint": "لديك {{entity}} غير مكتمل منذ {{when}}.",
      "continue": "متابعة",
      "discard": "تجاهل"
    },
    "status": {
      "saving": "جارٍ الحفظ…",
      "saved": "تم حفظ التغييرات"
    },
    "conflict": "تغيّرت هذه المسودة في نافذة أخرى. سيُعتمد آخر تعديل عند الحفظ.",
    "page": {
      "title": "عمل غير مكتمل",
      "lede": "مسودات بدأتها ولم تكملها. تابع من حيث توقفت أو احذفها.",
      "empty": "لا توجد مسودات غير مكتملة.",
      "lastUpdated": "آخر تعديل {{when}}",
      "continue": "متابعة",
      "discard": "تجاهل"
    }
  },
```

- [ ] **Step 3: Write the recovery banner**

Create `apps/web/src/components/DraftRecoveryBanner.tsx`:

```tsx
import { useTranslation } from "react-i18next";

import { relativeTime } from "../lib/relativeTime";
import "./DraftRecoveryBanner.css";

interface Props {
  /** Human label for what's being recovered, e.g. the translated "customer". */
  entityLabel: string;
  /** ISO timestamp of the draft's last activity. */
  lastActiveAt: string;
  onContinue: () => void;
  onDiscard: () => void;
}

/**
 * Calm "Continue where you left off?" surface shown when an unfinished draft is detected on entry.
 * No colour in the frame (monochrome chrome); the one primary button carries the recommended action.
 */
export function DraftRecoveryBanner({ entityLabel, lastActiveAt, onContinue, onDiscard }: Props) {
  const { t, i18n } = useTranslation();
  return (
    <div className="draft-recovery" role="status">
      <div className="draft-recovery__text">
        <p className="draft-recovery__title">{t("drafts.recovery.title")}</p>
        <p className="draft-recovery__hint">
          {t("drafts.recovery.hint", { entity: entityLabel, when: relativeTime(lastActiveAt, i18n.language) })}
        </p>
      </div>
      <div className="draft-recovery__actions">
        <button type="button" className="btn btn--primary btn--sm" onClick={onContinue}>
          {t("drafts.recovery.continue")}
        </button>
        <button type="button" className="btn btn--sm btn--ghost" onClick={onDiscard}>
          {t("drafts.recovery.discard")}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write the banner CSS**

Create `apps/web/src/components/DraftRecoveryBanner.css`:

```css
.draft-recovery {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
  margin-block-end: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-elevated);
}

.draft-recovery__title {
  font-weight: 600;
  color: var(--color-text);
}

.draft-recovery__hint {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}

.draft-recovery__actions {
  display: flex;
  gap: var(--space-2);
  flex-shrink: 0;
}
```

> If any token name above (`--space-4`, `--radius-md`, `--color-surface-elevated`, `--text-sm`, …) does not exist in `apps/web/src/styles/tokens.css`, substitute the nearest existing token — do NOT introduce a raw value. Confirm names against `tokens.css` before finishing this step.

- [ ] **Step 5: Write the status indicator**

Create `apps/web/src/components/DraftStatusIndicator.tsx`:

```tsx
import { useTranslation } from "react-i18next";

import "./DraftStatusIndicator.css";

interface Props {
  status: "idle" | "saving" | "saved";
  savedAt: Date | null;
}

/** Subtle inline "Saving… / Changes saved" text. Renders nothing until the first save begins. */
export function DraftStatusIndicator({ status, savedAt }: Props) {
  const { t } = useTranslation();
  if (status === "idle" && !savedAt) return null;
  const label = status === "saving" ? t("drafts.status.saving") : t("drafts.status.saved");
  return (
    <span className="draft-status" data-state={status} aria-live="polite">
      {label}
    </span>
  );
}
```

- [ ] **Step 6: Write the status indicator CSS**

Create `apps/web/src/components/DraftStatusIndicator.css`:

```css
.draft-status {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  transition: opacity var(--motion-fast) ease;
}

.draft-status[data-state="saving"] {
  opacity: 0.7;
}
```

- [ ] **Step 7: Verify parity + types**

Run (from `apps/web`): `node scripts/check-i18n-parity.mjs`
Expected: PASS (ar/en have identical key sets).
Run: `npx tsc --noEmit`
Expected: no new errors.

- [ ] **Step 8: Commit**

```bash
git add apps/web/src/components/DraftRecoveryBanner.tsx apps/web/src/components/DraftRecoveryBanner.css apps/web/src/components/DraftStatusIndicator.tsx apps/web/src/components/DraftStatusIndicator.css apps/web/src/i18n/locales/en.json apps/web/src/i18n/locales/ar.json
git commit -m "feat(web): add draft recovery banner + status indicator + i18n"
```

---

## Task 8: Drafts surface (`/drafts` page + route)

**Files:**
- Create: `apps/web/src/pages/drafts/DraftsPage.tsx`, `apps/web/src/pages/drafts/drafts.css`
- Modify: `apps/web/src/App.tsx` (add the route)

**Interfaces:**
- Consumes: `listDrafts`, `discardDraft` (Task 5); `useAsync` (existing hook); `relativeTime`; `EmptyState` (existing component); `drafts.page.*` i18n (Task 7).
- Produces: a route at `/drafts` listing the user's active drafts (workflow label, last-updated, Continue, Discard).

- [ ] **Step 1: Write the page**

Create `apps/web/src/pages/drafts/DraftsPage.tsx`. Each row's **Continue** navigates to the workflow that owns the draft. For Smart-Import drafts (`workflow_key === "imports.smart.create"`, `related_entity_id` = the batch id) it routes to `/imports/{batchId}`; for the create-form drafts it routes to that form's page (the create form re-detects its own draft on mount and shows the recovery banner). Use a small map from `workflow_key` → route.

```tsx
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { listDrafts, discardDraft, type WorkSessionDraft } from "../../api/workSessions";
import { useAsync } from "../../hooks/useAsync";
import { EmptyState } from "../../components/EmptyState";
import { relativeTime } from "../../lib/relativeTime";
import "./drafts.css";

// Where "Continue" sends the user for each workflow. The create forms re-detect their own draft on
// mount (recovery banner); Smart Import resumes by batch id (its existing resume-by-URL path).
function routeFor(d: WorkSessionDraft): string {
  switch (d.workflow_key) {
    case "sales.customer.create":
      return "/sales/customers";
    case "inventory.item.create":
      return "/inventory/items";
    case "sales.order.create":
      return "/sales/orders/new";
    case "purchasing.order.create":
      return "/purchasing/orders/new";
    case "imports.smart.create":
      return d.related_entity_id ? `/imports/${d.related_entity_id}` : "/imports/new";
    default:
      return "/";
  }
}

export function DraftsPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { data: drafts, loading, reload } = useAsync(listDrafts, [], "worksessions:drafts");

  const rows = useMemo(() => drafts ?? [], [drafts]);

  async function onDiscard(id: string) {
    await discardDraft(id).catch(() => {});
    reload();
  }

  return (
    <section className="page-enter drafts-page">
      <header className="drafts-page__head">
        <h1 className="drafts-page__title">{t("drafts.page.title")}</h1>
        <p className="drafts-page__lede">{t("drafts.page.lede")}</p>
      </header>

      {!loading && rows.length === 0 ? (
        <EmptyState title={t("drafts.page.empty")} />
      ) : (
        <ul className="drafts-list">
          {rows.map((d) => (
            <li key={d.id} className="drafts-list__row card">
              <div className="drafts-list__text">
                <span className="drafts-list__name">
                  {t(`drafts.workflow.${d.workflow_key}`, { defaultValue: d.entity_type || d.workflow_key })}
                </span>
                <span className="drafts-list__when muted">
                  {t("drafts.page.lastUpdated", { when: relativeTime(d.last_active_at, i18n.language) })}
                </span>
              </div>
              <div className="drafts-list__actions">
                <button type="button" className="btn btn--sm btn--primary" onClick={() => navigate(routeFor(d))}>
                  {t("drafts.page.continue")}
                </button>
                <button type="button" className="btn btn--sm btn--ghost" onClick={() => onDiscard(d.id)}>
                  {t("drafts.page.discard")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Add per-workflow labels to i18n**

In `en.json` under the existing `drafts` block, add a `workflow` map; mirror it in `ar.json`:

en.json:
```json
    "workflow": {
      "sales.customer.create": "Customer draft",
      "inventory.item.create": "Item draft",
      "sales.order.create": "Sales order draft",
      "purchasing.order.create": "Purchase order draft",
      "imports.smart.create": "Import in progress"
    }
```
ar.json:
```json
    "workflow": {
      "sales.customer.create": "مسودة عميل",
      "inventory.item.create": "مسودة صنف",
      "sales.order.create": "مسودة أمر بيع",
      "purchasing.order.create": "مسودة أمر شراء",
      "imports.smart.create": "استيراد قيد التنفيذ"
    }
```

- [ ] **Step 3: Write the page CSS**

Create `apps/web/src/pages/drafts/drafts.css`:

```css
.drafts-page__head {
  margin-block-end: var(--space-4);
}

.drafts-page__title {
  font-size: var(--text-xl);
  font-weight: 600;
}

.drafts-page__lede {
  color: var(--color-text-muted);
}

.drafts-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  list-style: none;
  padding: 0;
  margin: 0;
}

.drafts-list__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) var(--space-4);
}

.drafts-list__text {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.drafts-list__name {
  font-weight: 600;
}

.drafts-list__actions {
  display: flex;
  gap: var(--space-2);
  flex-shrink: 0;
}
```

> Confirm token names against `tokens.css`; substitute the nearest existing token if any differ.

- [ ] **Step 4: Register the route**

In `apps/web/src/App.tsx`, import `DraftsPage` and add a route alongside the other top-level authenticated routes:

```tsx
import { DraftsPage } from "./pages/drafts/DraftsPage";
```
```tsx
<Route path="/drafts" element={<DraftsPage />} />
```
(Match the exact `<Route>` nesting/wrapper the neighbouring routes use in this file.)

- [ ] **Step 5: Verify parity, types, build**

Run (from `apps/web`): `node scripts/check-i18n-parity.mjs` → PASS.
Run: `npx tsc --noEmit` → no new errors.
Run: `npm run test` → existing suite still green.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/pages/drafts apps/web/src/App.tsx apps/web/src/i18n/locales/en.json apps/web/src/i18n/locales/ar.json
git commit -m "feat(web): add /drafts surface listing unfinished work"
```

---

## Task 9: Wire create-customer (the proof) — `CustomersPage.tsx`

**Files:**
- Modify: `apps/web/src/pages/sales/CustomersPage.tsx`

**Interfaces:**
- Consumes: `useDraftRecovery` (Task 6), `DraftRecoveryBanner` + `DraftStatusIndicator` (Task 7).
- Draft contract: `workflowKey = "sales.customer.create"`, `entityType = t("party.customer")`, payload = the create-form fields.

**Context:** The create form lives on the customers list page (state around `CustomersPage.tsx:98-107`: `code`, `name`, `limit`, `taxReg`, `nationalId`, `customValues`; toggled by `showForm`; submitted in `onSubmit` near line 131 which calls `createCustomer`). Read the file first to match its exact structure.

- [ ] **Step 1: Read the target file**

Read `apps/web/src/pages/sales/CustomersPage.tsx` fully so the edits below land on the real variable names and JSX.

- [ ] **Step 2: Build the draft object + baseline**

In the create-form component, derive a single `draft` object from the existing field state and a constant `baseline` (all-empty). Place near the other `useMemo`/derived values:

```tsx
const draft = useMemo(
  () => ({ code, name, limit, taxReg, nationalId, customValues }),
  [code, name, limit, taxReg, nationalId, customValues],
);
const DRAFT_BASELINE = { code: "", name: "", limit: "", taxReg: "", nationalId: "", customValues: {} };
```

(If `prefill` seeds initial values, keep `DRAFT_BASELINE` as the truly-empty shape — a prefilled duplicate is itself meaningful and worth preserving.)

- [ ] **Step 3: Call the hook**

```tsx
const recovery = useDraftRecovery({
  workflowKey: "sales.customer.create",
  value: draft,
  baseline: DRAFT_BASELINE,
  schemaVersion: 1,
  entityType: t("party.customer"),
});
```

- [ ] **Step 4: Render the recovery banner + status indicator**

Just inside the form (above the fields), render the banner when a draft is recoverable, and the status indicator near the submit button:

```tsx
{recovery.recoverable && (
  <DraftRecoveryBanner
    entityLabel={t("party.customer")}
    lastActiveAt={recovery.recoverable.lastActiveAt}
    onContinue={() => {
      const p = recovery.recover();
      if (p) {
        setCode(p.code); setName(p.name); setLimit(p.limit);
        setTaxReg(p.taxReg); setNationalId(p.nationalId); setCustomValues(p.customValues);
        setShowForm(true);
      }
    }}
    onDiscard={() => void recovery.discard()}
  />
)}
```
```tsx
<DraftStatusIndicator status={recovery.status} savedAt={recovery.savedAt} />
```

- [ ] **Step 5: Mark complete after a successful create**

In `onSubmit`, after `createCustomer(...)` resolves successfully (in the optimistic `request`'s success path, where the form is reset — near `setCode(""); setName("");`), call:

```tsx
void recovery.complete();
```
Ensure it runs only on success, not on validation failure or a rejected request.

- [ ] **Step 6: Type-check + build**

Run (from `apps/web`): `npx tsc --noEmit` → no new errors.
Run: `npm run test` → green.

- [ ] **Step 7: Manual browser verification**

Start the app (see project run steps). Then:
1. Open Customers → open the create form → type a name + phone. Watch "Saving… → Changes saved".
2. Navigate away (e.g. to Dashboard) WITHOUT saving; return to Customers → open the create form.
   Expected: the "Continue where you left off?" banner. Click **Continue** → fields restored.
3. Reload the browser tab mid-entry (before any blur), return to the form → banner appears (server draft survived the reload).
4. Click **Discard** → banner clears; reopening the form shows no banner.
5. Complete a real create → reopen the form → no banner (the draft was completed, not re-offered).

- [ ] **Step 8: Commit**

```bash
git add apps/web/src/pages/sales/CustomersPage.tsx
git commit -m "feat(web): draft recovery for create-customer"
```

---

## Task 10: Wire create-item — `ItemsPage.tsx`

**Files:**
- Modify: `apps/web/src/pages/inventory/ItemsPage.tsx`

**Interfaces:** identical pattern to Task 9. `workflowKey = "inventory.item.create"`, `entityType = t("inventory.item.title")` (use the existing item label key this file already imports; if unsure, reuse whatever label the page shows for a single item).

- [ ] **Step 1: Read the target file**

Read `apps/web/src/pages/inventory/ItemsPage.tsx` to find the create-form field state (SKU, name, uom, type, reorder point, customValues) and its submit/reset path calling `createItem`.

- [ ] **Step 2: Build draft + baseline**

```tsx
const draft = useMemo(
  () => ({ sku, name, uom, type, reorderPoint, customValues }),
  [sku, name, uom, type, reorderPoint, customValues],
);
const DRAFT_BASELINE = { sku: "", name: "", uom: "", type: "stock", reorderPoint: "", customValues: {} };
```
(Match the real state variable names in the file — adjust keys accordingly.)

- [ ] **Step 3: Call the hook**

```tsx
const recovery = useDraftRecovery({
  workflowKey: "inventory.item.create",
  value: draft,
  baseline: DRAFT_BASELINE,
  schemaVersion: 1,
  entityType: t("inventory.item.title"),
});
```

- [ ] **Step 4: Render banner + status; restore on Continue**

Render `<DraftRecoveryBanner>` when `recovery.recoverable`, and on **Continue** call each field's setter from the recovered payload (mirror Task 9 Step 4 with this page's setters), then open the form. Render `<DraftStatusIndicator>` by the submit button.

- [ ] **Step 5: Complete after a successful create**

After `createItem(...)` succeeds (the form-reset path), call `void recovery.complete();`.

- [ ] **Step 6: Verify**

`npx tsc --noEmit` → clean; `npm run test` → green. Manual: repeat Task 9 Step 7 for items.

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/pages/inventory/ItemsPage.tsx
git commit -m "feat(web): draft recovery for create-item"
```

---

## Task 11: Wire create sales order — `NewOrderPage.tsx`

**Files:**
- Modify: `apps/web/src/pages/sales/NewOrderPage.tsx`

**Interfaces:** `workflowKey = "sales.order.create"`. Payload includes the header fields + the `lines` array (draft lines are strings — safe to serialize as-is).

- [ ] **Step 1: Read the target file**

Read `apps/web/src/pages/sales/NewOrderPage.tsx` (its shape mirrors `NewPurchaseOrderPage.tsx`: `customer`/`warehouse`/`taxCode` + `lines: DraftLine[]`, `onSubmit` calling `createOrder`).

- [ ] **Step 2: Build draft + baseline**

```tsx
const draft = useMemo(
  () => ({ customer, warehouse, taxCode, notes, lines }),
  [customer, warehouse, taxCode, notes, lines],
);
const DRAFT_BASELINE = { customer: "", warehouse: "", taxCode: "", notes: "", lines: [emptyLine()] };
```
(Use the file's real state names and its `emptyLine()`. If a `duplicate`/prefill seeds initial state, keep BASELINE as the empty shape so a duplicated draft is still preserved.)

- [ ] **Step 3: Call the hook**

```tsx
const recovery = useDraftRecovery({
  workflowKey: "sales.order.create",
  value: draft,
  baseline: DRAFT_BASELINE,
  schemaVersion: 1,
  entityType: t("sales.orders.order"),
});
```
(Use the file's existing "sales order" label key; substitute the correct one if `sales.orders.order` isn't present.)

- [ ] **Step 4: Render banner + status; restore on Continue**

Render `<DraftRecoveryBanner>` above the form when `recovery.recoverable`; on **Continue**, apply the recovered payload with the page's setters (`setCustomer`, `setWarehouse`, `setTaxCode`, `setNotes`, `setLines`). Render `<DraftStatusIndicator>` near the submit button.

- [ ] **Step 5: Complete after a successful create**

In `onSubmit`, after `createOrder(...)` resolves and before `navigate(...)`, call `void recovery.complete();`.

- [ ] **Step 6: Verify**

`npx tsc --noEmit` → clean; `npm run test` → green. Manual: enter a customer + one line, navigate away, return → banner → Continue restores lines. Reload mid-entry → banner. Complete a real order → no banner.

- [ ] **Step 7: Commit**

```bash
git add apps/web/src/pages/sales/NewOrderPage.tsx
git commit -m "feat(web): draft recovery for create sales order"
```

---

## Task 12: Wire create purchase order — `NewPurchaseOrderPage.tsx`

**Files:**
- Modify: `apps/web/src/pages/purchasing/NewPurchaseOrderPage.tsx`

**Interfaces:** `workflowKey = "purchasing.order.create"`. Payload = `supplier`, `warehouse`, `taxCode`, `lines`. This file's structure is known (state at lines 48-57, `onSubmit` near line 83 calling `createPurchaseOrder`, then `navigate`).

- [ ] **Step 1: Build draft + baseline**

Near the derived `subtotal`/`vat` values:

```tsx
const draft = useMemo(
  () => ({ supplier, warehouse, taxCode, lines }),
  [supplier, warehouse, taxCode, lines],
);
const DRAFT_BASELINE = { supplier: "", warehouse: "", taxCode: "", lines: [emptyLine()] };
```

- [ ] **Step 2: Call the hook**

```tsx
const recovery = useDraftRecovery({
  workflowKey: "purchasing.order.create",
  value: draft,
  baseline: DRAFT_BASELINE,
  schemaVersion: 1,
  entityType: t("purchasing.orders.order"),
});
```
(Substitute the file's real "purchase order" label key if `purchasing.orders.order` isn't present.)

- [ ] **Step 3: Render banner + status; restore on Continue**

Above `<WorkflowTracker …>` inside the form, render the banner when `recovery.recoverable`; on **Continue** call `setSupplier`, `setWarehouse`, `setTaxCode`, `setLines` from the payload. Put `<DraftStatusIndicator status={recovery.status} savedAt={recovery.savedAt} />` in the `pur-actions` row beside the submit button.

- [ ] **Step 4: Complete after a successful create**

In `onSubmit`, right after `const order = await createPurchaseOrder({...})` and before `navigate(...)`:

```tsx
void recovery.complete();
```

- [ ] **Step 5: Verify**

`npx tsc --noEmit` → clean; `npm run test` → green. Manual: pick a supplier + one line, switch browser tab away and back (visibilitychange flush), reload → banner → Continue restores. Complete a real PO → no banner.

- [ ] **Step 6: Commit**

```bash
git add apps/web/src/pages/purchasing/NewPurchaseOrderPage.tsx
git commit -m "feat(web): draft recovery for create purchase order"
```

---

## Task 13: Wire Smart Import pointer — `UploadStep.tsx` (+ `ImportWizard.tsx`)

**Files:**
- Modify: `apps/web/src/pages/imports/UploadStep.tsx` (create the WorkSession pointer once a batch exists)
- Modify (if needed): `apps/web/src/pages/imports/ImportWizard.tsx` (complete the pointer when the run finishes)

**Interfaces:** `workflowKey = "imports.smart.create"`, `relatedEntityId = batchId`. The `ImportBatch` remains the source of truth (rows/validation/progress); the WorkSession only records "an import is in progress" so it appears on `/drafts` and can be resumed. Payload is minimal (`{ step }`).

**Rationale:** Do NOT rebuild import persistence. Reuse the existing durable batch + resume-by-URL path (`ImportWizard` already routes by batch status). We add one `saveDraft` at batch creation and one `completeDraft` when the batch reaches a terminal state.

- [ ] **Step 1: Read the target files**

Read `apps/web/src/pages/imports/UploadStep.tsx` and re-read `ImportWizard.tsx` (already in context) to find where the batch id first exists (upload response → `onDetected`/`onMapped`) and where the run reaches `done`/`failed`/`rolled_back` (`RunStep`).

- [ ] **Step 2: Create the pointer when a batch is created**

In `UploadStep.tsx`, after the upload response yields a `batch_id`, record the pointer (best-effort; a failure must not block the wizard). Import `saveDraft` from `../../api/workSessions`:

```tsx
import { saveDraft } from "../../api/workSessions";
```
```tsx
// Best-effort: register a resumable "import in progress" pointer so it appears on /drafts and can
// be resumed. The ImportBatch itself remains the durable source of truth.
void saveDraft({
  workflow_key: "imports.smart.create",
  related_entity_id: String(batchId),
  payload: { step: "map" },
  entity_type: "import",
  schema_version: 1,
  client_version: 1,
}).catch(() => {});
```
(Place this where `batchId` is first known — the upload result handler.)

- [ ] **Step 3: Complete the pointer when the run finishes**

Where the wizard observes a terminal batch status (`done` / `rolled_back` / `failed`) — in `RunStep` after the report loads, or in `ImportWizard`'s resume effect when `RUN_STATUSES` includes a terminal status — mark the pointer complete. Since the pointer is keyed by batch id, look it up via the active-draft endpoint and complete it. Add a helper in `api/workSessions.ts` usage:

```tsx
import { getActiveDraft, completeDraft } from "../../api/workSessions";
```
```tsx
// On a terminal import status, retire the resumable pointer (keeps /drafts clean).
void getActiveDraft("imports.smart.create", String(batchId))
  .then((d) => { if (d) return completeDraft(d.id, String(batchId)); })
  .catch(() => {});
```
Guard it so it runs once per terminal transition (e.g. a `useRef` fired-flag), mirroring the existing `firedIntro` pattern in the detail pages.

- [ ] **Step 4: Verify**

`npx tsc --noEmit` → clean; `npm run test` → green. Manual:
1. Upload a file, reach mapping. Open `/drafts` in another tab → "Import in progress" row; **Continue** → `/imports/{id}` resumes at the right step (existing behaviour).
2. Finish the import (run to `done`). `/drafts` → the import pointer no longer appears.
3. Confirm the existing import resume-by-reload still works unchanged.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/imports/UploadStep.tsx apps/web/src/pages/imports/ImportWizard.tsx
git commit -m "feat(web): register Smart Import as a resumable draft pointer"
```

---

## Final verification (run before declaring Project 1 done)

- [ ] Backend: `python -m pytest erp/worksessions/tests -q` → all pass.
- [ ] Backend: `python manage.py check` → no issues.
- [ ] Frontend (from `apps/web`): `node scripts/check-i18n-parity.mjs` → pass.
- [ ] Frontend: `npx tsc --noEmit` → clean.
- [ ] Frontend: `npm run test` → green (includes `draftRecovery.test.ts`).
- [ ] Brand: `python scripts/gates/gate03.py` (repo root) → pass; then run the `conductor-brand` brand-feel checklist on the recovery banner, status indicator, and `/drafts` page.
- [ ] Acceptance walk-through (manual): for customer, item, sales order, purchase order — enter data, leave, return, recover; reload mid-entry, recover; discard; complete → no re-offer. For Smart Import — resume from `/drafts`.

---

## Self-Review (completed while writing)

**1. Spec coverage (Project 1 scope):**
- §4.1 model → Task 1. §4.2 service → Task 2. §4.3 API → Task 3. §4.4 tests → Tasks 2–3.
- §5.1 hook → Task 6. §5.2 pure lib + Vitest → Task 4. §5.3 banner/indicator/drafts surface/client → Tasks 5, 7, 8. §5.4 wiring (5 flows) → Tasks 9–13.
- §7 cross-cutting: survives unload → Task 6 flush; no `beforeunload` → confirmed (none added); RBAC → Tasks 2,3; atomicity/no-duplicate-records → service never writes business models (Task 2), completion flips status only (Tasks 9–13); ar/en parity → Task 7 + gate; Smart-Import reuse → Task 13.
- §8 gates → Final verification.
- **Project 2 (spec §6) is intentionally out of scope** for this plan — it needs new backend PATCH contracts and per-entity "immutable fields" decisions; it gets its own plan (`2026-07-24-draft-recovery-project2.md`) after Project 1 lands. This is the brainstorming/writing-plans scope-split, agreed with the user.

**2. Placeholder scan:** No "TBD"/"TODO"/"handle edge cases". The only deferred detail is "match the file's real state variable names," which is inherent to editing existing files — each such task starts with a "read the target file" step and shows the exact edit shape.

**3. Type consistency:** `upsert_draft`/`UpsertResult`/`get_active`/`list_active`/`complete`/`discard` names match across Tasks 2, 3. Frontend `saveDraft`/`getActiveDraft`/`discardDraft`/`completeDraft`/`flushDraft` + `WorkSessionDraft`/`DraftSaveBody` match across Tasks 5, 6, 8, 13. `useDraftRecovery` return shape (`status`/`savedAt`/`recoverable`/`recover`/`discard`/`complete`/`conflict`) is consumed consistently in Tasks 9–12. `workflow_key` values match between the drafts-surface `routeFor` map (Task 8) and each wiring task's `workflowKey`.
