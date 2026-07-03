// Typed wrappers for the AI assistant API (/api/assistant/*). The assistant is an optional layer:
// /status says whether it's on (no key ⇒ off ⇒ every AI surface stays hidden). Extraction is
// read-only — it returns a proposal the user reviews; the confirm step posts through the normal
// purchasing endpoint, so no money ever moves through this API.
import { ApiError, apiFetch, apiUpload, getToken, refreshAccess } from "./client";
import i18n from "../i18n";
import type { PageContext } from "../assistant/context";

export interface AssistantStatus {
  enabled: boolean;
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
  type: "order" | "customer" | "item";
  value: string;
  label: string;
}

export interface AskAnswer {
  answer: string;
  citations: AskCitation[];
  used_tool: string | null;
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

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  // Server-attached extras (the answer's citations, the turn's attachments); read-only to the client.
  meta: { citations?: AskCitation[]; attachments?: AttachmentInfo[] } & Record<string, unknown>;
  created_at: string;
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
  type: "token" | "citations" | "done" | "error";
  text?: string;
  citations?: AskCitation[];
  message_id?: number;
  // Which data tool answered — the client maps it to curated follow-up questions (session 06).
  used_tool?: string | null;
  message?: string;
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

export async function chatStream(
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
  const send = () =>
    fetch("/api/assistant/chat", {
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
