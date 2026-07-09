"""Gate 15 -- eval smoke (ai-reliability T1.10, non-blocking).

Replays the golden dataset offline against its recorded fixtures (zero network -- see
``erp/assistant/evals/runner.py``) and compares the pass rate against the Phase 1 baseline
recorded in ``Docs/plan/ai-reliability-roadmap/BASELINE.md`` (74.3%, measured 2026-07-10).

Non-blocking by design (per the roadmap: "threshold = baseline - 5 points ... becomes blocking in
Phase 8"): a drop below threshold prints a warning and still exits 0. Only a hard crash of the
runner itself (missing dataset, import error) fails the gate -- a quality regression is signal for
a human, not a merge blocker, until continuous evaluation (Phase 8) lands.
"""
from __future__ import annotations

BASELINE_PASS_RATE = 0.743  # Docs/plan/ai-reliability-roadmap/BASELINE.md, measured 2026-07-10
THRESHOLD_POINTS = 0.05
THRESHOLD = BASELINE_PASS_RATE - THRESHOLD_POINTS


def check() -> None:
    from erp.assistant.evals.runner import run_all

    result = run_all()
    graded = result["pass"] + result["fail"]
    if graded == 0:
        print("GATE 15 WARN: no graded eval cases (no recordings present) -- skipping threshold check")
        return

    pass_rate = result["pass_rate"]
    print(f"GATE 15 eval smoke: {result['pass']}/{graded} pass ({pass_rate:.1%}), "
          f"threshold {THRESHOLD:.1%} (baseline {BASELINE_PASS_RATE:.1%} - {THRESHOLD_POINTS:.0%})")
    if pass_rate < THRESHOLD:
        print(f"GATE 15 WARN: eval pass rate {pass_rate:.1%} below threshold {THRESHOLD:.1%} "
              f"-- non-blocking for now, becomes blocking in Phase 8")
