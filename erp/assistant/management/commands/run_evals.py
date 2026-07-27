"""Grade the golden eval set offline (ai-reliability T1.6) — recorded responses only, zero
network. Prints a scoreboard and writes ``evals/results/<date>.json``.

``--suite retrieval`` (ai-reliability T3.3) instead runs the offline retrieval suite: it builds the
committed fixture corpus in a rolled-back transaction, scores the fts / blend / fusion strategies
with recall@5/10, MRR, nDCG@10, and writes both a dated result and the baseline-vs-fusion
comparison. Deterministic and offline (fixture embeddings) — no provider, no pgvector binary.

``--suite long_thread`` (ai-reliability T3.7) runs the rolling-summary continuity suite: 5 golden
cases proving a fact planted early in a thread is still reachable by the planner's envelope once
the thread outgrows the raw-history tail and a summary refresh has fired."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...evals import loader, long_thread, retrieval, runner

RESULTS_DIR = Path(__file__).resolve().parents[2] / "evals" / "results"
COMPARISON_PATH = RESULTS_DIR / "retrieval_baseline_vs_fusion.json"


class Command(BaseCommand):
    help = "Grade the golden eval set offline against recorded responses (zero network)."

    def add_arguments(self, parser):
        parser.add_argument("--suite", choices=["golden", "retrieval", "long_thread"],
                            default="golden",
                            help="'golden' (default) replays recorded ask/agent cases; "
                                 "'retrieval' runs the offline retrieval metric suite (T3.3); "
                                 "'long_thread' runs the rolling-summary continuity suite (T3.7)")
        parser.add_argument("--min", type=float, default=0.0,
                            help="minimum pass rate (0-1) required; exits non-zero below it")

    def handle(self, *args, **options):
        if options["suite"] == "retrieval":
            return self._handle_retrieval(options)
        if options["suite"] == "long_thread":
            return self._handle_long_thread(options)
        return self._handle_golden(options)

    # --- golden suite (T1.6) --------------------------------------------------------------------

    def _handle_golden(self, options):
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

    # --- retrieval suite (T3.3) -----------------------------------------------------------------

    def _handle_retrieval(self, options):
        # The fixture corpus is built in a real transaction and rolled back, so a dev DB is never
        # polluted by an eval run (under pytest the test transaction rolls back on its own).
        scoreboard = self._score_retrieval_rolled_back()
        report = retrieval.comparison_report(scoreboard)

        self.stdout.write(
            f"Retrieval suite: {scoreboard['corpus_docs']} docs, {scoreboard['queries']} queries "
            f"({scoreboard['queries_ar']} ar / {scoreboard['queries_en']} en)")
        for name in retrieval.STRATEGIES:
            overall = scoreboard["strategies"][name]["overall"]
            self.stdout.write(
                f"  {name:<7} recall@5={overall['recall@5']:.3f} recall@10={overall['recall@10']:.3f} "
                f"MRR={overall['mrr']:.3f} nDCG@10={overall['ndcg@10']:.3f}")
        self.stdout.write("fusion vs blend (delta): " + ", ".join(
            f"{k}={v:+.3f}" for k, v in report["fusion_vs_blend"].items()))

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        dated = RESULTS_DIR / f"retrieval_{date.today().isoformat()}.json"
        dated.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        COMPARISON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(f"\nWrote {dated}\nWrote {COMPARISON_PATH}")

    def _score_retrieval_rolled_back(self) -> dict:
        sentinel = RuntimeError("rollback")
        holder: dict = {}
        try:
            with transaction.atomic():
                holder["scoreboard"] = retrieval.score_suite()
                raise sentinel  # unwind the transaction — fixtures must not persist
        except RuntimeError as exc:
            if exc is not sentinel:
                raise
        return holder["scoreboard"]

    # --- long-thread continuity suite (T3.7) ------------------------------------------------------

    def _handle_long_thread(self, options):
        scoreboard = long_thread.score_suite()

        self.stdout.write(f"Long-thread suite: {scoreboard['total']} cases")
        self.stdout.write(f"pass={scoreboard['pass']} fail={scoreboard['fail']} "
                          f"pass_rate={scoreboard['pass_rate']:.0%}")
        for r in scoreboard["results"]:
            if r["status"] == "fail":
                self.stdout.write(self.style.ERROR(f"  [fail] {r['id']} ({r['lang']})"))

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = RESULTS_DIR / f"long_thread_{date.today().isoformat()}.json"
        out_path.write_text(json.dumps(scoreboard, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(f"\nWrote {out_path}")

        if scoreboard["pass_rate"] < options["min"]:
            raise CommandError(
                f"pass rate {scoreboard['pass_rate']:.0%} below --min {options['min']:.0%}")
