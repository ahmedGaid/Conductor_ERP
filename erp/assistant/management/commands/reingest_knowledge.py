"""Rebuild every ``KnowledgeChunk``'s tsvector from the ai-reliability T3.4 normalized text shadow
(``erp.assistant.textnorm.normalize_ar``, applied by ``services.knowledge._index_search_vectors``).

Documents ingested before the normalizer shipped have a tsvector built from raw text; this command
brings them in line with new ingestions without touching the stored (raw) ``text`` column or any
embedding. Throttled and resumable: walks chunks in id order, sleeping between batches so a large
knowledge base doesn't spike the DB. Idempotent by construction — the tsvector is a pure
recomputation from ``text`` on every run, so re-running (or resuming after an interruption) always
converges to the same result; no separate "already done" bookkeeping is needed.

    .\\.venv\\Scripts\\python.exe manage.py reingest_knowledge --batch 200 --sleep 0.5
"""
from __future__ import annotations

import time

from django.contrib.postgres.search import SearchVector
from django.core.management.base import BaseCommand
from django.db.models import Value

from erp.assistant import textnorm
from erp.assistant.models import KnowledgeChunk


class Command(BaseCommand):
    help = "Rebuild every knowledge chunk's tsvector from the T3.4 normalized text shadow."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--batch", type=int, default=200, help="rows per batch (default 200)")
        parser.add_argument("--sleep", type=float, default=0.5,
                            help="seconds to pause between batches (default 0.5)")

    def handle(self, *args, batch: int, sleep: float, **options) -> None:
        updated = 0
        last_id = 0
        while True:
            rows = list(
                KnowledgeChunk.objects.filter(id__gt=last_id)
                .order_by("id").values_list("id", "text")[:batch]
            )
            if not rows:
                break
            for chunk_id, text in rows:
                last_id = chunk_id
                KnowledgeChunk.objects.filter(id=chunk_id).update(
                    search=SearchVector(Value(textnorm.normalize_ar(text)), config="simple")
                )
                updated += 1
            if sleep > 0:
                time.sleep(sleep)

        self.stdout.write(self.style.SUCCESS(f"knowledge tsvectors reindexed: {updated}"))
