"""Calibrate the LLM-as-judge grader against a hand-labeled set (ai-reliability T1.7): LIVE judge
calls only, never runs by accident — needs both ``ASSISTANT_ENABLED`` and ``--yes-live``. Judge
verdicts don't count toward eval pass rates until this reports >= 90% agreement with the human
labels in ``calibration_v1.jsonl``.
"""
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ... import client as assistant_client
from ...evals import graders

CALIBRATION_PATH = (
    Path(__file__).resolve().parents[2] / "evals" / "datasets" / "calibration_v1.jsonl"
)
RESULTS_PATH = Path(__file__).resolve().parents[2] / "evals" / "results" / "judge_calibration.json"

REQUIRED_AGREEMENT = 0.90


def _load_pairs() -> list[dict]:
    return [json.loads(line) for line in CALIBRATION_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()]


class Command(BaseCommand):
    help = "Calibrate the LLM-as-judge grader against calibration_v1.jsonl (live, dev only)."

    def add_arguments(self, parser):
        parser.add_argument("--yes-live", action="store_true", dest="yes_live",
                            help="required — confirms this makes real, billed provider calls")

    def handle(self, *args, **options):
        if not assistant_client.enabled():
            raise CommandError("ASSISTANT_ENABLED is off — set it before calibrating live.")
        if not options["yes_live"]:
            raise CommandError("This makes real, billed provider calls. Pass --yes-live to confirm.")

        pairs = _load_pairs()
        mismatches = []
        agree_count = 0
        for pair in pairs:
            case = {"input": pair["input"], "expected": {"judge": pair["rubric"]}}
            output = {"answer": pair["answer"]}
            judge_pass, judge_reason = graders.grade_judge(case, output)
            if judge_pass == pair["expected_pass"]:
                agree_count += 1
            else:
                mismatches.append({
                    "id": pair["id"], "expected_pass": pair["expected_pass"],
                    "judge_pass": judge_pass, "judge_reason": judge_reason,
                })

        rate = agree_count / len(pairs) if pairs else 0.0
        self.stdout.write(f"agreement: {rate:.0%} ({agree_count}/{len(pairs)})")
        for m in mismatches:
            self.stdout.write(self.style.WARNING(
                f"  mismatch {m['id']}: expected {m['expected_pass']} got {m['judge_pass']} "
                f"({m['judge_reason']})"))

        RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULTS_PATH.write_text(json.dumps({
            "agreement": rate, "total": len(pairs), "required": REQUIRED_AGREEMENT,
            "mismatches": mismatches,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(f"\nWrote {RESULTS_PATH}")

        if rate < REQUIRED_AGREEMENT:
            raise CommandError(f"judge agreement {rate:.0%} below required {REQUIRED_AGREEMENT:.0%}")
