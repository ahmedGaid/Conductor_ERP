"""Backfill the pgvector ``embedding_v`` column from the legacy JSON ``embedding`` (T3.1).

Throttled and resumable: processes chunks that already have a JSON embedding but no vector one, in
id order, sleeping between batches so a large corpus doesn't spike the DB. Idempotent — a row with
a vector is skipped, so running twice fills the same set of rows and no more.

    .\\.venv\\Scripts\\python.exe manage.py backfill_embeddings --batch 200 --sleep 0.5

No-op (with a warning) when the pgvector column is absent — i.e. an install where migration 0010
skipped it because the server has no ``vector`` extension.
"""
from __future__ import annotations

import json
import time

from django.core.management.base import BaseCommand
from django.db import connection

from erp.assistant.services import knowledge


class Command(BaseCommand):
    help = "Copy JSON chunk embeddings into the pgvector embedding_v column (throttled, resumable)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--batch", type=int, default=200, help="rows per batch (default 200)")
        parser.add_argument("--sleep", type=float, default=0.5,
                            help="seconds to pause between batches (default 0.5)")

    def handle(self, *args, batch: int, sleep: float, **options) -> None:
        if not knowledge._has_vector_column():
            self.stdout.write(self.style.WARNING(
                "pgvector column absent (migration 0010 skipped — no `vector` extension on this "
                "server). Nothing to backfill."
            ))
            return

        filled = 0
        skipped = 0
        last_id = 0
        while True:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT id, embedding FROM assistant_knowledgechunk "
                    "WHERE embedding IS NOT NULL AND embedding_v IS NULL AND id > %s "
                    "ORDER BY id LIMIT %s",
                    [last_id, batch],
                )
                rows = cur.fetchall()
            if not rows:
                break
            for chunk_id, emb in rows:
                last_id = chunk_id
                vec = emb if isinstance(emb, list) else json.loads(emb)
                try:
                    knowledge._write_vector_column(chunk_id, vec)
                    filled += 1
                except ValueError:
                    # dimension mismatch (an old embedding from a different model) — leave the row
                    # untouched rather than crash the whole backfill; report the count at the end.
                    skipped += 1
            if sleep > 0:
                time.sleep(sleep)

        msg = f"embedding_v backfilled: {filled}"
        if skipped:
            msg += f" ({skipped} skipped — dimension mismatch)"
        self.stdout.write(self.style.SUCCESS(msg))
