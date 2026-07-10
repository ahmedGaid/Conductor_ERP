"""Compare a task class's baseline model against a candidate model (ai-reliability T2.4): prints
pass rate + estimated cost/case and the promotion verdict, writes
``evals/results/routing_<task>_<model>.json``. The baseline side always runs offline against
``evals/recordings/`` — no key needed. The candidate side needs ``--yes-live`` (same gate as
``record_evals``/``calibrate_judge``): omit it to get a baseline-only report, or to re-print a
prior live run's saved result without spending again.

    manage.py eval_routing --task ask --candidate groq:meta-llama/llama-4-scout-17b-16e-instruct
    manage.py eval_routing --task ask --candidate groq:meta-llama/llama-4-scout-17b-16e-instruct --yes-live
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ... import client as assistant_client
from ...evals import routing_report


class Command(BaseCommand):
    help = "Compare a task class's baseline model against a candidate on the golden eval set."

    def add_arguments(self, parser):
        parser.add_argument("--task", required=True,
                            help="task class from ASSISTANT_ROUTING, e.g. ask, agent_plan, digest")
        parser.add_argument("--candidate", required=True,
                            help="'provider:model', e.g. groq:meta-llama/llama-4-scout-17b-16e-instruct")
        parser.add_argument("--yes-live", action="store_true", dest="yes_live",
                            help="actually call the candidate live (real, billed provider calls); "
                                 "omit to score the baseline offline and re-print any prior live result")

    def handle(self, *args, **options):
        task, candidate = options["task"], options["candidate"]
        candidate_scoreboard = None
        if options["yes_live"]:
            if not assistant_client.enabled():
                raise CommandError("ASSISTANT_ENABLED is off — set it before recording live.")
            try:
                candidate_scoreboard = routing_report.run_candidate_live(task, candidate)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc

        try:
            report = routing_report.build_report(
                task, candidate, candidate_scoreboard=candidate_scoreboard)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        baseline, cand = report["baseline"], report["candidate"]
        self.stdout.write(
            f"task={task}  baseline={baseline['model']} ({baseline['cases_graded']} graded)")
        self.stdout.write(f"  pass_rate={self._fmt_rate(baseline['pass_rate'])} "
                          f"cost/case={self._fmt_cost(baseline)}")
        if cand:
            source = "live" if report["candidate_live"] else "prior live run"
            self.stdout.write(f"candidate={candidate} ({cand['cases_graded']} graded, {source})")
            self.stdout.write(f"  pass_rate={self._fmt_rate(cand['pass_rate'])} "
                              f"cost/case={self._fmt_cost(cand)}")
        else:
            self.stdout.write(self.style.WARNING(
                "candidate not evaluated — pass --yes-live to score it (real, billed calls)"))
        self.stdout.write(f"rule: {report['rule']}")

        verdict = report["promote"]
        if verdict is True:
            self.stdout.write(self.style.SUCCESS("PROMOTE"))
        elif verdict is False:
            self.stdout.write(self.style.WARNING("KEEP BASELINE"))
        else:
            self.stdout.write("NOT ENOUGH DATA")

        path = routing_report.write_report(report, candidate)
        self.stdout.write(f"\nWrote {path}")

    @staticmethod
    def _fmt_rate(rate):
        return f"{rate:.0%}" if rate is not None else "n/a"

    @staticmethod
    def _fmt_cost(side):
        if side["cost_unknown"]:
            return "unknown model"
        if side["cost_microcents_per_case"] is None:
            return "n/a"
        return f"{side['cost_microcents_per_case']:.1f} microcents"
