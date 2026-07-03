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

// --- Streaming chat (plan session 02) ----------------------------------------------------------
// The chat endpoint answers over an SSE stream so the reply renders as the model writes. One
// `data:` JSON per event; sessions 09/10 add more event types to the same union.

export interface ChatEvent {
  type: "token" | "citations" | "done" | "error";
  text?: string;
  citations?: AskCitation[];
  message_id?: number;
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
  body: { conversation_id: number; message: string; context?: PageContext },
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
