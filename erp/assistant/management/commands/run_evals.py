"""Grade the golden eval set offline (ai-reliability T1.6) — recorded responses only, zero
network. Prints a scoreboard and writes ``evals/results/<date>.json``."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ...evals import loader, runner

RESULTS_DIR = Path(__file__).resolve().parents[2] / "evals" / "results"


class Command(BaseCommand):
    help = "Grade the golden eval set offline against recorded responses (zero network)."

    def add_arguments(self, parser):
        parser.add_argument("--min", type=float, default=0.0,
                            help="minimum pass rate (0-1) required; exits non-zero below it")

    def handle(self, *args, **options):
        cases = loader.load_cases()
        scoreboard = runner.run_all(cases)

        self.stdout.write(
            f"Cases: {scoreboard['total_cases']}  recorded: {scoreboard['recorded_cases']}  "
            f"skipped (no recording): {scoreboard['skipped_no_recording']}"
        )
        self.stdout.write(
            f"pass={scoreboard['pass']} fail={scoreboard['fail']} "
            f"needs_judge={scoreboard['needs_judge']} no_runner={scoreboard['no_runner']} "
            f"error={scoreboard['error']}  pass_rate={scoreboard['pass_rate']:.0%}"
        )
        self.stdout.write("\nBy feature:")
        for feature, counts in sorted(scoreboard["by_feature"].items()):
            self.stdout.write(f"  {feature}: {counts}")
        self.stdout.write("By language:")
        for lang, counts in sorted(scoreboard["by_lang"].items()):
            self.stdout.write(f"  {lang}: {counts}")

        for r in scoreboard["results"]:
            if r["status"] in ("fail", "error"):
                self.stdout.write(self.style.ERROR(f"  [{r['status']}] {r['id']}: {r['reason']}"))

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = RESULTS_DIR / f"{date.today().isoformat()}.json"
        out_path.write_text(json.dumps(scoreboard, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(f"\nWrote {out_path}")

        if scoreboard["pass_rate"] < options["min"]:
            raise CommandError(
                f"pass rate {scoreboard['pass_rate']:.0%} below --min {options['min']:.0%}")
