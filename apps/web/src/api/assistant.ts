// Typed wrappers for the AI assistant API (/api/assistant/*). The assistant is an optional layer:
// /status says whether it's on (no key ⇒ off ⇒ every AI surface stays hidden). Extraction is
// read-only — it returns a proposal the user reviews; the confirm step posts through the normal
// purchasing endpoint, so no money ever moves through this API.
import { apiFetch, apiUpload } from "./client";

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

export function askAssistant(question: string): Promise<AskAnswer> {
  return apiFetch<AskAnswer>("/assistant/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
