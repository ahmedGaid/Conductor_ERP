# SESSION 13 — Attachments & Camera Capture
# Files: apps/mobile/lib/presentation/widgets/attachments/** + attachment data layer (new),
#        record screens' attachment sections (09–12 stubs), share-intent landing page (new)

**Objective:** files everywhere they exist on web — view, download, share — plus the phone's
superpowers: capture a document with the camera straight onto a record, pick from gallery/files,
and receive files SHARED FROM OTHER APPS (WhatsApp invoice PDF → share → Conductor → attach to a
record or hand to the AI). Uploads survive bad networks via a resumable upload queue.

---

## Before You Start

1. Find web's attachment endpoints (the assistant's attachment flow + any per-record attachment
   API) → upload contract, size limits, allowed types, how attachments bind to records.
2. Read current docs: `image_picker` (camera capture + gallery), `file_picker`, `share_plus`
   (outbound share), and **inbound share-intent handling** — Flutter has no first-party receiver;
   the standard package is `receive_sharing_intent` (Android intent-filter + iOS share
   extension). It is NOT on the approved list: adding it is a one-line DECISIONS entry at
   execution time (ground rule 6) — or hand-rolled platform channels if the package is
   unmaintained by then (READ its state; decide in the session).
3. Open the AI workspace plan's attachment session (`ai-workspace-plan/FILE_07_*`) → mobile must
   reuse the same server understanding pipeline, not invent one.

"Do not write anything yet."

---

## Task A — Attachment section (drop-in for every RecordScreen)

1. `AttachmentList`: thumbnails grid (images) + file rows (PDF/XLSX/etc. with own-set type
   icons), uploader name + time. Tap image → full-screen viewer (`InteractiveViewer` pinch-zoom —
   built in, no new dep); tap PDF → OS open/share handoff (do NOT add a heavy PDF-render dep for
   v1 — OS handoff is honest; note in PARITY.md).
2. Add ("إضافة مرفق") AppSheet: camera / gallery / files. Camera path: capture via `image_picker`
   → lightweight crop preview (accept/retake; skip fancy edge-detection in v1 — note as future) →
   compress (longest edge ~2000 px, JPEG ~0.8 — constants in one place; `image_picker`'s
   `maxWidth`/`imageQuality` params do this without a new dep) → queue.
3. Wire into sessions 09–12 stub sections (customer, invoice, item, supplier, PO…). One
   widget, every record type.

## Task B — Upload queue (drift table + worker)

1. drift table `uploads(id, recordRef, localPath, status, attempts, createdAt)`. Statuses:
   queued → uploading → done | failed.
2. Behaviour: sequential uploads, retry with backoff (3 attempts then "failed" with tap-to-retry
   row state), survives app restart (rescan on boot — datasource uses the `_ready` init pattern,
   `flutter-lessons` issue 3), cancellable. UI: the attachment shows immediately with a quiet
   progress ring (optimistic), failure state is designed (blame-free: "لم يكتمل الرفع — أعد
   المحاولة").
3. This queue is deliberately attachment-only; the general write queue (session 16) may later
   absorb its lessons — do not couple them now.

## Task C — Receive shares

1. Configure the inbound share intent (Android intent-filter; iOS share extension per the Task
   Before-You-Start decision): images + PDFs + spreadsheets.
2. Landing screen when a file arrives: preview + two actions — "إرفاق بسجل" (record search →
   attach via Task B) and "إرسال إلى المساعد" (session 14 wires the handoff; until then, stub
   behind the AI tab with the file pre-staged).
3. Cold-start share (app killed) must work; locked app → unlock first, file survives.

---

## Smoke Test

- [ ] Photograph a paper doc onto an invoice → appears on WEB's attachment list for the same
      record within seconds
- [ ] Airplane mode capture → queued state visible → restore network → auto-uploads; kill the
      app while queued → reopen → still uploads
- [ ] 3-attempt failure (point base URL at a dead port temporarily) → designed failed state →
      tap retry after fixing → succeeds
- [ ] Share a PDF from WhatsApp → Conductor appears in the OS share sheet → attach to a customer
      → verify on web; repeat with app killed beforehand
- [ ] Image viewer zooms; PDF opens via OS; download + OS share of an existing web-uploaded file
      works
- [ ] Size/type limits enforced with translated messages (server rules mirrored in copy, server
      still the enforcer)
- [ ] RTL + dark pass on all new surfaces; analyze + test + parity green; PARITY.md attachment
      rows flipped

## Risks

- iOS share extensions are the fiddliest territory (native extension target + app group) →
  timebox; if it fights back, ship Android share first and log iOS as a tracked issue — do NOT
  let this session stall the plan.
- Storage bloat from captures → compress before queue; clear local copies after confirmed upload.

---

## After This Session

```
Smoke test passed?
→ Commit, rename with _done → /compact → open FILE_14_AI_WORKSPACE.md
Phase 2 complete — natural merge checkpoint.
```
