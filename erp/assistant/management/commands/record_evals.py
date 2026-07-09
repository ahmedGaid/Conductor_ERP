"""Record LIVE provider responses for golden cases into ``evals/recordings/<case_id>.json`` — a
human runs this once (or after a prompt/model change) to refresh the fixtures the offline runner
(``run_evals``) replays. Never runs by accident: needs both ``ASSISTANT_ENABLED`` and
``--yes-live``. Only ``ask``/``agent`` cases are recordable today — ``extract`` needs real
document bytes (not a golden case's ``document_text``) and ``suggest`` has no service yet.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from ... import client as assistant_client
from ...evals import loader
from ...evals.runner import RECORDINGS_DIR, eval_actor, patched_tools
from ...services import agent as agent_service
from ...services import ask as ask_service


class _Recorder:
    """Wraps the real ``complete_json`` / ``complete_stream`` so live calls still happen — the
    provider's actual response is both returned (the run behaves normally) and captured."""

    def __init__(self):
        self.json_responses: list[dict] = []
        self.stream_responses: list[str] = []

    def wrap_json(self, original):
        def _wrapped(*args, **kwargs):
            result = original(*args, **kwargs)
            self.json_responses.append(result)
            return result
        return _wrapped

    def wrap_stream(self, original):
        def _wrapped(*args, **kwargs):
            chunks: list[str] = []
            for chunk in original(*args, **kwargs):
                chunks.append(chunk)
                yield chunk
            self.stream_responses.append("".join(chunks))
        return _wrapped


class Command(BaseCommand):
    help = "Make LIVE provider calls to record ask/agent golden-case fixtures (dev only)."

    def add_arguments(self, parser):
        parser.add_argument("--yes-live", action="store_true", dest="yes_live",
                            help="required — confirms this makes real, billed provider calls")
        parser.add_argument("--ids", nargs="*", default=None,
                            help="only record these case ids (default: every ask/agent case)")

    def handle(self, *args, **options):
        if not assistant_client.enabled():
            raise CommandError("ASSISTANT_ENABLED is off — set it before recording live.")
        if not options["yes_live"]:
            raise CommandError("This makes real, billed provider calls. Pass --yes-live to confirm.")

        cases = loader.load_cases()
        if options["ids"]:
            wanted = set(options["ids"])
            cases = [c for c in cases if c["id"] in wanted]

        actor = eval_actor()
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        written = 0
        for case in cases:
            if case["feature"] not in ("ask", "agent"):
                self.stdout.write(
                    f"skip {case['id']}: no live recorder for feature {case['feature']!r} yet")
                continue
            recorder = _Recorder()
            saved = {
                "ask_json": ask_service.complete_json,
                "agent_json": agent_service.complete_json,
                "agent_stream": agent_service.complete_stream,
            }
            try:
                ask_service.complete_json = recorder.wrap_json(saved["ask_json"])
                agent_service.complete_json = recorder.wrap_json(saved["agent_json"])
                agent_service.complete_stream = recorder.wrap_stream(saved["agent_stream"])
                with patched_tools(case["fixtures"]):
                    if case["feature"] == "ask":
                        ask_service.answer_question(
                            question=case["input"]["message"], actor=actor, conversation=None)
                    else:
                        from ...models import Conversation

                        conversation = Conversation.objects.create(user=actor)
                        try:
                            list(agent_service.run(
                                actor=actor, conversation=conversation,
                                question=case["input"]["message"]))
                        finally:
                            conversation.delete()
            finally:
                ask_service.complete_json = saved["ask_json"]
                agent_service.complete_json = saved["agent_json"]
                agent_service.complete_stream = saved["agent_stream"]

            path = RECORDINGS_DIR / f"{case['id']}.json"
            path.write_text(json.dumps({
                "json_responses": recorder.json_responses,
                "stream_responses": recorder.stream_responses,
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            written += 1
            self.stdout.write(f"recorded {case['id']} -> {path.name}")

        self.stdout.write(f"\n{written} recording(s) written.")
