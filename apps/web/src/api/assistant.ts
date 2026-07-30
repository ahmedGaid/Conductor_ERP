// Typed wrappers for the AI assistant API (/api/assistant/*). The assistant is an optional layer:
// /status says whether it's on (no key ⇒ off ⇒ every AI surface stays hidden). Extraction is
// read-only — it returns a proposal the user reviews; the confirm step posts through the normal
// purchasing endpoint, so no money ever moves through this API.
import { ApiError, apiFetch, apiUpload, getToken, refreshAccess } from "./client";
import i18n from "../i18n";
import type { PageContext } from "../assistant/context";

export interface AssistantStatus {
  enabled: boolean;
  // T2.9: "full" (every provider closed, no budget exhausted) · "degraded" (a fallback chain
  // or a blocked budget is in play, but a usable provider remains) · "down" (every provider
  // breaker-open — the next call would fail before trying).
  mode: "full" | "degraded" | "down";
}

export interface SupplierCandidate {
  code: string;
  name: string;
  score: number;
}

export interface ItemCandidate {
  sku: string;
  name: string;
  score: number;
}

export interface ExtractedLine {
  description: string;
  quantity: string;
  unit_price_minor: number | null;
  matched_sku: string | null;
  candidates: ItemCandidate[];
}

export interface ExtractProposal {
  readable: boolean;
  confidence: "high" | "medium" | "low";
  issues: string[];
  supplier: {
    name: string | null;
    tax_id: string | null;
    matched_code: string | null;
    candidates: SupplierCandidate[];
  };
  invoice: {
    number: string | null;
    date: string | null;
    currency: string;
    subtotal_minor: number | null;
    vat_minor: number | null;
    total_minor: number | null;
  };
  lines: ExtractedLine[];
}

export function assistantStatus(): Promise<AssistantStatus> {
  return apiFetch<AssistantStatus>("/assistant/status");
}

export function extractDocument(file: File): Promise<ExtractProposal> {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<ExtractProposal>("/assistant/extract-document", form);
}

// --- Chat attachments (plan session 07) --------------------------------------------------------
// A file uploads on its own first (chip shows while it transfers); the next send claims it. Mirrors
// the server allowlist + 5 MB cap so bad files are rejected instantly, before any upload.

export const MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024;

export const ALLOWED_ATTACHMENT_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
  "text/csv",
  "application/csv",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/json",
  "text/json",
  "application/xml",
  "text/xml",
  "text/plain",
]);

export interface AttachmentInfo {
  id: number;
  name: string;
  content_type: string;
  size: number;
}

export function uploadAttachment(file: File): Promise<AttachmentInfo> {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<AttachmentInfo>("/assistant/attachments", form);
}

// --- Natural-language assistant (part 2) -------------------------------------------------------

export interface AskCitation {
  // A real record the answer is built from — click-through so every number is verifiable.
  // "order" is a sales order (value = id); "purchaseOrder"/"journal" resolve by number,
  // "supplier"/"customer"/"item" by their business code/SKU. "document" is a company knowledge-
  // base doc (value = title, no separate label — the title IS the display text).
  type: "order" | "customer" | "item" | "supplier" | "purchaseOrder" | "journal" | "document";
  value: string;
  label?: string;
  document_id?: number;
  section?: number;
}

export interface AskAnswer {
  answer: string;
  citations: AskCitation[];
  used_tool: string | null;
  // T3.9: a below-confidence document search — the answer is a designed decline, not a grounded
  // one; the client renders it as the no-answer card instead of a normal answer bubble.
  low_confidence?: boolean;
}

export function askAssistant(question: string, context?: PageContext): Promise<AskAnswer> {
  return apiFetch<AskAnswer>("/assistant/ask", {
    method: "POST",
    body: JSON.stringify({ question, context }),
  });
}

// --- Conversations (plan session 01 API, wired for the threads UI in session 05) ---------------
// Each conversation is private to its owner (the server filters to request.user and 404s a foreign
// id). The list is the workspace's thread history; a conversation opens to its messages.

export interface ConversationSummary {
  id: number;
  title: string;
  pinned: boolean;
  archived: boolean;
  updated_at: string;
  preview: string;
}

// One step the agent took to answer (session 09): a tool call the model chose, with a human label
// ("why") and whether it succeeded. Streamed live as `step` events, then persisted in the answer's
// meta so a reloaded thread still shows the "Checked N sources" reasoning summary.
export interface ChatStep {
  tool: string;
  // `label` while streaming (the live `why`); `why` when read back from a persisted message.
  label?: string;
  why?: string;
  ok?: boolean;
  state?: "running" | "done";
}

// The context-budget meter for one turn (ai-reliability T3.6): how much of the model's window this
// answer used, and whether the envelope manager had to trim or drop anything to fit.
export interface EnvelopeInfo {
  tokens: number;
  budget: number;
  compacted: boolean;
}

// A record link on a proposal/result card — a real record the action touches or created.
export interface ActionRecord {
  type: "customer" | "supplier" | "item" | "order" | "purchaseRequest" | "purchaseOrder" | "quotation";
  value: string;
  label: string;
}

// A write the agent prepared for the user to confirm (plan session 10). Nothing is created until a
// confirm; the proposal rides in the assistant message meta, so a reloaded thread shows its settled
// state. `payload` is server-only detail the client never needs (kept optional/opaque here).
export interface ActionProposal {
  action: string;
  summary: string[];
  records: ActionRecord[];
  risks: string[];
  total: string | null;
  affected: number;
  status: "pending" | "confirmed" | "dismissed";
  // Present once confirmed: the created document's link + a success line. `verifier` rides along
  // when the action declared invariants (os-foundations FILE_03) — absent for undeclared actions,
  // no behaviour change.
  result?: { summary: string; links: ActionRecord[]; verifier?: ActionVerifier };
  // Present only for risk="post" actions (agent-posting-plan FILE_01): the retype-confirm the card
  // must show before Confirm is enabled — label is display text, minor is what must be retyped.
  challenge?: { label: string; minor: number };
}

// One post-write check pass (os-foundations FILE_03 T3.2) — a failure never reaches the client as
// this shape; it 422s instead and the card shows the blame-free error line.
export interface ActionVerifier {
  ok: true;
  packs: string[];
}

// A near-match the user can pick when a reference was ambiguous (plan session 12).
export interface SuggestionCandidate {
  code: string;
  name: string;
  score: number;
}

// One permission-filtered way out of a blocker. The server sends ONLY what the actor may use —
// the client renders whatever arrives and never decides permissions itself.
export interface SuggestionOption {
  kind: "inline_action" | "deep_link" | "review_candidates" | "open_record";
  // inline_action: the session-10 action to run from chat (via a follow-up message).
  action?: string;
  args?: Record<string, unknown>;
  // deep_link / open_record: a real app route; `prefill` rides in the URL for the create form.
  label_key?: string;
  to?: string;
  prefill?: Record<string, string>;
  expect?: { entity: string; query: string };
  // review_candidates: near matches with scores; picking one maps it and continues.
  entity?: string;
  candidates?: SuggestionCandidate[];
}

// A blocker turned actionable (plan session 12): issue → permitted fixes → the resume promise.
// Rides in the assistant message meta like a proposal; session 13 flips `status` to "resolved".
export interface AssistantSuggestion {
  issue: { kind: "missing" | "inactive" | "ambiguous"; entity: string; query: string };
  options: SuggestionOption[];
  no_permission: string | null;
  resume: string;
  status: "open" | "resolved";
}

// --- Bulk import (plan session 14) -------------------------------------------------------------
// A spreadsheet the agent read: its columns mapped to a target's fields, stepped through
// mapping → preview → report. Rides in the assistant message meta like a proposal, so a reloaded
// thread shows the same stage; execute persists the report back for reload-safety.

// One field of an import target (the create form's shape) — drives the mapping dropdowns.
export interface ImportField {
  key: string;
  label: string;
  required: boolean;
}

// field key → the file column carrying it (or null when unmapped/ignored).
export type ImportMapping = Record<string, string | null>;

export interface ImportRowError {
  row: number;
  field: string;
  message: string;
}

export interface ImportPreview {
  valid: number;
  errors: ImportRowError[];
  duplicates: { row: number; key: string }[];
  // First parsed rows (each a field→value map plus its 1-based `row`), for the peek table.
  rows: Record<string, string | number>[];
}

export interface ImportReportRow {
  row: number;
  status: "created" | "skipped" | "error";
  key: string;
  message: string;
}

export interface ImportReport {
  created: number;
  skipped: number;
  errors: ImportRowError[];
  report: ImportReportRow[];
  links: ActionRecord[];
}

export interface ImportTask {
  attachment_id: number;
  target: "customers" | "suppliers" | "items";
  fields: ImportField[];
  columns: string[];
  mapping: ImportMapping;
  sample: Record<string, string>[];
  row_count: number;
  issues: string[];
  stage: "mapping" | "report";
  // Filled once the batch is executed (server-persisted, reload-safe).
  report?: ImportReport;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  // Server-attached extras (the answer's citations, the turn's attachments, the agent's steps, a
  // write proposal); read-only to the client.
  meta: {
    citations?: AskCitation[];
    attachments?: AttachmentInfo[];
    steps?: ChatStep[];
    proposal?: ActionProposal;
    suggestion?: AssistantSuggestion;
    import?: ImportTask;
    envelope?: EnvelopeInfo;
    // A synthetic "detour_return" user turn (session 13): rendered as a calm localised divider, not a
    // raw bubble. entity/label localise its text ("Back from creating supplier ABC Trading").
    kind?: string;
    entity?: string;
    label?: string;
    // T3.9: a below-confidence document search — rendered as the designed no-answer card.
    low_confidence?: boolean;
  } & Record<string, unknown>;
  created_at: string;
}

// Confirm or dismiss a proposal. Confirm runs the module contract as the caller and returns the
// created document's link; single-use (a second confirm 409s).
export interface ActionResult {
  status: "confirmed" | "dismissed";
  summary?: string;
  links?: ActionRecord[];
  followups?: string[];
  verifier?: ActionVerifier;
  deduplicated?: boolean;
}

export function executeAction(
  messageId: number,
  decision: "confirm" | "dismiss",
  typedMinor?: number,
): Promise<ActionResult> {
  return apiFetch<ActionResult>("/assistant/actions/execute", {
    method: "POST",
    body: JSON.stringify({
      message_id: messageId,
      decision,
      ...(typedMinor !== undefined ? { typed_minor: typedMinor } : {}),
    }),
  });
}

// --- Simulation (os-foundations FILE_05) -------------------------------------------------------
// A dry-run of a plan of write-actions: every step runs for real inside one transaction that always
// rolls back, so nothing persists. The diff is what WOULD happen — the "see it before it happens"
// card. Phase A/B's preview surfaces render this same shape.

// One step's outcome in the dry run. `ok` false = the step (or its post-write verifier) refused;
// the plan stops there and `summary` carries the blame-free reason.
export interface SimulationStep {
  action: string;
  summary: string | null;
  ok: boolean;
  // Present when the action declared invariants (FILE_02): which packs ran, and whether they held.
  verifier?: { ok: boolean; packs: string[] };
}

export interface SimulationDiff {
  ok: boolean;
  steps: SimulationStep[];
  // entity kind -> how many rows the plan would create, e.g. { customer: 3, sales_order: 14 }.
  creates: Record<string, number>;
  // Trial-balance movement the plan would post (minor units) — zero for draft-only plans.
  gl: { debit_delta_minor: number; credit_delta_minor: number };
  stock: { item: string; warehouse: string; delta: string }[];
  money: { receivables_delta_minor: number; payables_delta_minor: number };
}

// Preview one pending proposal the agent prepared (its stored, already-built payload is dry-run as a
// one-step plan). The server owns the payload — the client only names the message it rides on.
export function simulateProposal(messageId: number): Promise<SimulationDiff> {
  return apiFetch<SimulationDiff>("/assistant/simulate", {
    method: "POST",
    body: JSON.stringify({ message_id: messageId }),
  });
}

// Dry-run an explicit plan (Phase A/B). Kept exported alongside the proposal path — the endpoint is
// the same, only the input shape differs (≤10 steps, each an action + its build args).
export function simulatePlan(
  steps: { action: string; args?: Record<string, unknown> }[],
): Promise<SimulationDiff> {
  return apiFetch<SimulationDiff>("/assistant/simulate", {
    method: "POST",
    body: JSON.stringify({ steps }),
  });
}

// Dry-run a mapped import — parse + duplicate check, nothing written (plan session 14). Keyed by the
// import card's message; the server reads the file + target from its persisted meta, so the client
// only sends the column mapping the user adjusted.
export function previewImport(messageId: number, mapping: ImportMapping): Promise<ImportPreview> {
  return apiFetch<ImportPreview>("/assistant/imports/preview", {
    method: "POST",
    body: JSON.stringify({ message_id: messageId, mapping }),
  });
}

// Create the valid, non-duplicate rows (single-use — a second run 409s). The report is persisted
// back onto the card so a reload shows the settled outcome.
export function executeImport(messageId: number, mapping: ImportMapping): Promise<ImportReport> {
  return apiFetch<ImportReport>("/assistant/imports/execute", {
    method: "POST",
    body: JSON.stringify({ message_id: messageId, mapping }),
  });
}

// The server returns a flat detail object; keep the wire type internal and expose the split the UI
// wants (summary + messages).
interface ConversationDetail extends ConversationSummary {
  created_at: string;
  messages: ChatMessage[];
}

export function listConversations(q?: string, archived?: boolean): Promise<ConversationSummary[]> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (archived) params.set("archived", "1");
  const qs = params.toString();
  return apiFetch<ConversationSummary[]>(`/assistant/conversations${qs ? `?${qs}` : ""}`);
}

export function createConversation(): Promise<ConversationSummary> {
  return apiFetch<ConversationSummary>("/assistant/conversations", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getConversation(
  id: number,
): Promise<{ conversation: ConversationSummary; messages: ChatMessage[] }> {
  return apiFetch<ConversationDetail>(`/assistant/conversations/${id}`).then((d) => ({
    conversation: {
      id: d.id,
      title: d.title,
      pinned: d.pinned,
      archived: d.archived,
      updated_at: d.updated_at,
      preview: d.preview,
    },
    messages: d.messages,
  }));
}

export function updateConversation(
  id: number,
  patch: Partial<Pick<ConversationSummary, "title" | "pinned" | "archived">>,
): Promise<ConversationSummary> {
  return apiFetch<ConversationSummary>(`/assistant/conversations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
}

export function deleteConversation(id: number): Promise<void> {
  return apiFetch<void>(`/assistant/conversations/${id}`, { method: "DELETE" });
}

// --- Streaming chat (plan session 02) ----------------------------------------------------------
// The chat endpoint answers over an SSE stream so the reply renders as the model writes. One
// `data:` JSON per event; sessions 09/10 add more event types to the same union.

export interface ChatEvent {
  type:
    | "step"
    | "token"
    | "citations"
    | "done"
    | "error"
    | "proposal"
    | "suggestion"
    | "import"
    | "retrying";
  text?: string;
  citations?: AskCitation[];
  message_id?: number;
  // Which data tool answered — the client maps it to curated follow-up questions (session 06).
  used_tool?: string | null;
  message?: string;
  // `error` events (T2.7): the AppError catalog code, e.g. "AI-007" for a budget block — lets the
  // client show a designed message instead of the raw (English-only) backend string.
  code?: string;
  // `step` events (session 09): one tool call the agent is running / has finished.
  tool?: string;
  label?: string;
  state?: "running" | "done";
  ok?: boolean;
  // `proposal` event (session 10): a prepared write awaiting the user's confirm, keyed by message_id.
  proposal?: ActionProposal;
  // `suggestion` event (session 12): a blocker turned actionable, keyed by message_id.
  suggestion?: AssistantSuggestion;
  // `import` event (session 14): a mapping-stage spreadsheet import card, keyed by message_id.
  import?: ImportTask;
  // `done` event (ai-reliability T3.6): this turn's context-budget usage — lets the client render
  // a quiet meter and, when `compacted`, a calm "older parts were summarized" notice.
  conversation_tokens?: number;
  budget_tokens?: number;
  compacted?: boolean;
}

// Same auth headers apiFetch sends (bearer + Accept-Language). Kept local because a raw stream
// can't reuse apiFetch's envelope unwrap; it replicates only the header + one-shot 401 refresh.
function streamHeaders(): Record<string, string> {
  const token = getToken();
  return {
    "Content-Type": "application/json",
    "Accept-Language": i18n.resolvedLanguage || i18n.language || "ar",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// The shared SSE reader for every assistant stream (chat + detour resume): POST a JSON body, replay
// once through the refresh cookie on a 401, then dispatch each `data:` frame as a ChatEvent. Kept in
// one place so both streams share identical framing, auth and error handling.
async function sseStream(
  path: string,
  body: unknown,
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const send = () =>
    fetch(path, {
      method: "POST",
      headers: streamHeaders(),
      body: JSON.stringify(body),
      signal,
    });

  let res = await send();
  // Expired access token: renew through the refresh cookie once and replay (mirrors apiFetch).
  if (res.status === 401 && (await refreshAccess())) res = await send();

  if (!res.ok || !res.body) {
    let msg = `Request failed (${res.status})`;
    try {
      const env = (await res.json()) as { error?: { message?: unknown } };
      if (typeof env?.error?.message === "string") msg = env.error.message;
    } catch {
      /* non-JSON body — keep the generic message */
    }
    throw new ApiError(msg, res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let split: number;
      while ((split = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, split).trim();
        buffer = buffer.slice(split + 2);
        if (!frame.startsWith("data:")) continue;
        const payload = frame.slice("data:".length).trim();
        if (!payload) continue;
        try {
          onEvent(JSON.parse(payload) as ChatEvent);
        } catch {
          /* skip a malformed frame rather than tear down the stream */
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export function chatStream(
  body: {
    conversation_id: number;
    message?: string;
    context?: PageContext;
    // Re-answer the conversation's last question in place (retry / regenerate); no new user turn.
    regenerate?: boolean;
    // Ids of already-uploaded attachments to claim onto this turn (session 07).
    attachment_ids?: number[];
  },
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  return sseStream("/api/assistant/chat", body, onEvent, signal);
}

// Resume paused work after a guided detour (plan session 13). `message_id` is the suggestion turn;
// `resolved` is the record the user just created (or null → the server re-resolves by query). Streams
// the welcome-back over the same ChatEvent contract as chatStream.
export function resumeDetour(
  body: {
    conversation_id: number;
    message_id: number;
    resolved: { entity: string; id: string; label: string } | null;
  },
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  return sseStream("/api/assistant/detours/resume", body, onEvent, signal);
}

// --- Knowledge base (plan session 06) ------------------------------------------------------------
// Admin-managed documents the assistant can search and quote (search_documents tool, session 04).
// Ingestion is synchronous server-side; a row lands as "ready" or "failed" (with error_text), never
// as a thrown error to the uploader.

// Mirrors the server allowlist (erp/assistant/api/views.py ALLOWED_TYPES | KNOWLEDGE_TEXT_TYPES) so
// bad files are rejected instantly, before any upload.
export const ALLOWED_KNOWLEDGE_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "application/pdf",
  "text/plain",
  "text/markdown",
  "text/csv",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
]);

export interface KnowledgeDoc {
  id: number;
  title: string;
  filename: string;
  status: "processing" | "ready" | "failed";
  error_text: string;
  chunk_count: number;
  size: number;
  updated_at: string;
}

export function listKnowledge(): Promise<KnowledgeDoc[]> {
  return apiFetch<KnowledgeDoc[]>("/assistant/knowledge");
}

export function uploadKnowledge(file: File, title: string): Promise<KnowledgeDoc> {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  return apiUpload<KnowledgeDoc>("/assistant/knowledge", form);
}

export function deleteKnowledge(id: number): Promise<void> {
  return apiFetch<void>(`/assistant/knowledge/${id}`, { method: "DELETE" });
}

// --- memory (ai-reliability T4.4) ---------------------------------------------------------------

export type MemoryScope = "user" | "org";

export interface MemoryRow {
  id: number;
  kind: "slot" | "fact";
  key: string;
  value: string;
  source: "explicit" | "pattern" | "settings";
  confidence: number;
  created_at: string;
}

export interface MemoryProposal {
  kind: "memory_proposal";
  slot: string;
  value: string;
  occurrences: number;
  detector: string;
}

export interface MemoryListing {
  personal: MemoryRow[];
  org: MemoryRow[];
  slots: Record<string, string>;
  slot_keys: string[];
  proposal: MemoryProposal | null;
}

export function listMemory(): Promise<MemoryListing> {
  return apiFetch<MemoryListing>("/assistant/memory");
}

export function setMemorySlot(
  key: string,
  value: string,
  scope: MemoryScope = "user",
): Promise<{ id: number; key: string; value: string }> {
  return apiFetch<{ id: number; key: string; value: string }>("/assistant/memory", {
    method: "PUT",
    body: JSON.stringify({ key, value, scope }),
  });
}

export function forgetMemory(id: number, scope: MemoryScope = "user"): Promise<void> {
  return apiFetch<void>(`/assistant/memory/${id}?scope=${scope}`, { method: "DELETE" });
}

export function decideMemoryProposal(
  decision: "confirm" | "dismiss",
  slot: string,
  value: string,
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>("/assistant/memory/proposals", {
    method: "POST",
    body: JSON.stringify({ decision, slot, value }),
  });
}

// Ops view (ai-reliability T1.8) types/fetchers live in ./assistantOps — that page is route-split
// (App.tsx lazy-loads OpsPage), so keeping them out of this eagerly-loaded module keeps the main
// bundle inside its gzip budget (scripts/check-bundle-size.mjs).
