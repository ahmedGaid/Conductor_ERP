# SESSION 2 — Streaming Chat Endpoint (SSE)
# Files: erp/assistant/client.py, erp/assistant/api/views.py, erp/assistant/api/urls.py, erp/assistant/services/ask.py, apps/web/src/api/assistant.ts, erp/assistant/tests/test_chat_stream.py (new)

---

## Before You Start

1. Open `erp/assistant/client.py` → read `complete_json` and the three provider paths (`_gemini`,
   `_groq`, `_anthropic`), including the retry/backoff logic (the Gemini "client closed" fix —
   don't regress it) and how the active provider is chosen.
2. Open `erp/assistant/services/ask.py` → note where the final answer text is produced.
3. Open `apps/web/src/api/client.ts` → read `apiFetch` (auth headers, error envelope) — the
   streaming helper must send the same headers.
4. Open `erp/assistant/errors.py` → reuse its error types; don't invent new ones.

"Do not write anything yet."

---

## Task A — Provider streaming in client.py

Add to `erp/assistant/client.py` a sibling of `complete_json`:

```python
def complete_stream(messages, *, system: str | None = None):
    """Yield answer text chunks from the active provider.

    Falls back to a single yield of the full completion for any provider without a
    streaming path yet — callers never need to know the difference.
    """
```

Implement true streaming per provider using the SDKs already in the project (`stream=True` for the
Groq OpenAI-compatible client, `client.messages.stream` for Anthropic, `generate_content(...,
stream=True)` for Gemini). Reuse the existing key/config/backoff plumbing — same env vars, same
retry discipline. If a provider path is awkward, ship the fallback (one yield) for it and note it;
the SSE contract stays identical.

## Task B — SSE chat view

In `erp/assistant/api/views.py` add `ChatView` (`POST /api/assistant/chat`), same auth as `AskView`.
Body: `{"conversation_id": int, "message": str}`. Response: `StreamingHttpResponse` with
`content_type="text/event-stream"` and headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`.

Event protocol (one `data:` JSON per event — sessions 09/10 add more event types to this same
stream, so route everything through one serializer helper):

```
data: {"type": "token", "text": "..."}
data: {"type": "citations", "citations": [...]}
data: {"type": "done", "message_id": 123}
data: {"type": "error", "message": "..."}
```

Flow inside the generator: persist the user Message (session 1 helpers) → run the ask pipeline but
stream the final answer via `complete_stream` → accumulate chunks → persist the assistant Message →
emit `done`. Wrap the generator body in try/except: on exception emit an `error` event with a
human, blame-free message (reuse `errors.py` mapping) — never a stack trace. A client disconnect
(BrokenPipeError / ConnectionResetError) aborts generation quietly and still persists whatever text
was produced, so "cancel" costs nothing.

Register in `api/urls.py` below `ask`:

```python
    path("chat", ChatView.as_view(), name="assistant-chat"),
```

## Task C — Frontend streaming helper

In `apps/web/src/api/assistant.ts`, below `askAssistant`, add:

```typescript
export interface ChatEvent {
  type: "token" | "citations" | "done" | "error";
  text?: string;
  citations?: AskCitation[];
  message_id?: number;
  message?: string;
}

export async function chatStream(
  body: { conversation_id: number; message: string },
  onEvent: (e: ChatEvent) => void,
  signal?: AbortSignal,
): Promise<void>
```

Implement with `fetch` + `response.body.getReader()` + a line buffer that splits on `\n\n`, parses
`data: ` payloads, and calls `onEvent`. Send the exact same auth headers `apiFetch` sends (import
or replicate its header builder — read `client.ts` first). `signal` wires straight into `fetch` so
`AbortController.abort()` is the cancel button.

## Task D — Tests

`erp/assistant/tests/test_chat_stream.py`: mock `complete_stream` to yield 3 chunks; assert the
response streams `token`×3 → `done`, both messages persisted, and an unknown `conversation_id`
returns 404 before any streaming starts.

---

## Smoke Test

- [ ] `pytest erp/assistant` green
- [ ] `curl -N -X POST .../api/assistant/chat` with a valid body prints incremental `data:` lines
- [ ] Assistant reply persisted — visible via `GET /conversations/<id>`
- [ ] Kill curl mid-stream → server logs no traceback; partial text persisted
- [ ] Invalid conversation_id → single `error`/404, no stream
- [ ] `npx tsc --noEmit` green in `apps/web`

---

## After This Session

```
Smoke test passed?
→ Rename this file: append _done (e.g. FILE_01_CONVERSATIONS_BACKEND_done.md). A _done file is finished forever - never reopen it.
→ Type /compact in Claude Code
→ Open FILE_03_CONTEXT_ENVELOPE.md and continue
```
