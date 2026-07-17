"""`manage.py run_imports [--once]` — claim and drive ready/stale import batches to completion.

Long-running by default (loop with an idle sleep) under the same process supervisor as the app
server — see Docs/RUNBOOK.md and DECISIONS.md's "Smart Import — background runner" entry.
``--once`` processes at most one batch and exits (tests, cron). A batch left ``running`` with a
stale heartbeat — a process that died mid-batch — is recovered automatically by the next claim,
no human touching anything (spec step 20).
"""
from __future__ import annotations

import time

from django.core.management.base import BaseCommand

from erp.imports import runner

IDLE_SLEEP_SECONDS = 5


class Command(BaseCommand):
    help = "Claim and run ready (or stale-heartbeat) import batches — the smart-import background runner."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process at most one batch, then exit.")

    def handle(self, *args, **options):
        once = options["once"]
        while True:
            batch = runner.claim_next()
            if batch is None:
                if once:
                    self.stdout.write("No ready batch.")
                    return
                time.sleep(IDLE_SLEEP_SECONDS)
                continue

            report = runner.run(batch.created_by, batch)
            self.stdout.write(
                f"batch {batch.pk} ({batch.entity}): {report['status']} — "
                f"created={report['created']} updated={report['updated']} "
                f"skipped={report['skipped']} errors={report['errors']}"
            )
            if once:
                return
