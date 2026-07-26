"""Offline retrieval eval suite (ai-reliability T3.3).

Builds a small committed fixture corpus in the active DB, ingests it, runs real
``knowledge.search`` over a labelled query set, and scores three retrieval strategies with the pure
metrics in :mod:`retrieval_metrics`:

  * ``fts``    — Postgres full-text ranking only (the pre-embedding lexical baseline).
  * ``blend``  — the pre-fusion 0.5·tsrank + 0.5·cosine blend that T3.2 removed, reconstructed here
                 purely so the fusion change can be measured against what it replaced.
  * ``fusion`` — the current Reciprocal Rank Fusion path (``knowledge.search`` as shipped).

Fully offline and deterministic: provider embeddings are replaced by :func:`fixture_embed`, a
committed local bag-of-tokens vector (crc32-hashed, L2-normalized). No network, no API key, no
pgvector binary needed — the vector arm runs through the flag-off JSON-cosine path. The suite
therefore measures the ranking/fusion PIPELINE reproducibly; the absolute recall numbers are bounded
by the fixture embedding model, not by live Gemini vectors (stated in the results file).

Retrieval unit = the fixture document: every corpus doc is authored under ``CHUNK_CHARS`` so it
ingests to exactly one chunk, and a query's ``relevant`` map is keyed by ``doc_key``. Search rows
(which carry ``document_id``) are mapped back to ``doc_key`` through the build-time id map.
"""
from __future__ import annotations

import json
import re
import zlib
from contextlib import contextmanager
from pathlib import Path

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F

from ..models import KnowledgeChunk
from ..services import knowledge
from . import retrieval_metrics as metrics
from .runner import eval_actor

# The embedding seam is reached through ``knowledge.client`` (the module ``search`` itself calls),
# not a direct ``import client`` — so patching it here swaps exactly what search uses, and this eval
# harness stays off the gateway-invariant allowlist (``test_gateway_invariant``).

DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
CORPUS_PATH = DATASETS_DIR / "retrieval_corpus_v1.jsonl"
QUERIES_PATH = DATASETS_DIR / "retrieval_v1.jsonl"

STRATEGIES = ("fts", "blend", "fusion")
SEARCH_LIMIT = 10  # recall@10 is the widest metric, so retrieve at least that many

_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)  # letter runs (Arabic + Latin), drop digits/punct


# --- deterministic offline embedding ------------------------------------------------------------

def fixture_embed(text: str, *_args, dim: int = knowledge.EMBED_DIM, **_kwargs) -> list[float]:
    """A stable local embedding for eval fixtures: L2-normalized bag of crc32-hashed tokens.

    Topically similar texts share tokens, so their cosine similarity is high — enough to exercise
    the vector arm and rank fusion deterministically, with zero network. Signature tolerates the
    ``actor=``/``conversation_id=`` kwargs real ``embed_text`` accepts so it drops in as a patch.
    """
    vec = [0.0] * dim
    for token in _TOKEN_RE.findall((text or "").lower()):
        vec[zlib.crc32(token.encode("utf-8")) % dim] += 1.0
    norm = sum(x * x for x in vec) ** 0.5
    return [x / norm for x in vec] if norm else vec


@contextmanager
def fixture_embeddings():
    """Replace ``client.embed_text`` with :func:`fixture_embed` for the duration — used at both
    ingest (chunk vectors) and query time so the whole suite is offline and reproducible."""
    saved = knowledge.client.embed_text
    knowledge.client.embed_text = fixture_embed
    try:
        yield
    finally:
        knowledge.client.embed_text = saved


# --- data loading -------------------------------------------------------------------------------

def load_corpus(path: Path = CORPUS_PATH) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_queries(path: Path = QUERIES_PATH) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_corpus(corpus: list[dict], *, actor=None) -> dict[int, str]:
    """Ingest every fixture doc and return the ``{document_id: doc_key}`` map. Call inside
    :func:`fixture_embeddings` so chunk vectors are the deterministic fixture ones."""
    actor = actor or eval_actor()
    knowledge._reset_vector_cache()
    doc_map: dict[int, str] = {}
    for doc in corpus:
        row = knowledge.ingest_document(
            data=doc["text"].encode("utf-8"), media_type="text/plain",
            filename=f"{doc['doc_key']}.txt", title=doc["title"], actor=actor,
        )
        doc_map[row.id] = doc["doc_key"]
    return doc_map


# --- ranking strategies (each returns doc_keys, best first) -------------------------------------

def _rows_to_keys(rows: list[dict], doc_map: dict[int, str]) -> list[str]:
    """Map search rows to their ``doc_key``, de-duplicated, order preserved (a doc may in general
    surface via more than one chunk; fixtures are single-chunk, but stay correct regardless)."""
    keys: list[str] = []
    for row in rows:
        key = doc_map.get(row["document_id"])
        if key is not None and key not in keys:
            keys.append(key)
    return keys


def rank_fusion(query: str, doc_map: dict[int, str], *, limit: int = SEARCH_LIMIT) -> list[str]:
    """The shipped RRF path — ``knowledge.search`` as production runs it."""
    return _rows_to_keys(knowledge.search(query, limit=limit), doc_map)


def rank_fts(query: str, doc_map: dict[int, str], *, limit: int = SEARCH_LIMIT) -> list[str]:
    """Pure FTS baseline: force the vector arm off (no query embedding) so ``search`` degrades to
    the single-list FTS pass-through."""
    saved = knowledge.client.embed_text
    knowledge.client.embed_text = lambda *a, **k: None
    try:
        return _rows_to_keys(knowledge.search(query, limit=limit), doc_map)
    finally:
        knowledge.client.embed_text = saved


def rank_blend(query: str, doc_map: dict[int, str], *, limit: int = SEARCH_LIMIT) -> list[str]:
    """The removed pre-fusion baseline: 0.5·(tsrank / max_rank) + 0.5·cosine over the FTS
    candidate pool. Reconstructed here (not imported — T3.2 deleted it) only to measure fusion
    against what it replaced. Uses the fixture query embedding (caller is inside
    :func:`fixture_embeddings`)."""
    query = (query or "").strip()
    if not query:
        return []
    sq = SearchQuery(query, config="simple", search_type="websearch")
    candidates = list(
        KnowledgeChunk.objects.filter(document__status="ready", search=sq)
        .annotate(rank=SearchRank(F("search"), sq))
        .select_related("document")
        .order_by("-rank")[: limit * 4]
    )
    if not candidates:
        return []
    q_emb = knowledge.client.embed_text(query)
    max_rank = max((c.rank for c in candidates), default=0.0) or 1.0
    scored = []
    for c in candidates:
        if q_emb and c.embedding:
            score = 0.5 * (c.rank / max_rank) + 0.5 * knowledge._cosine(q_emb, c.embedding)
        else:
            score = c.rank
        scored.append((score, c))
    scored.sort(key=lambda t: t[0], reverse=True)
    keys: list[str] = []
    for _score, c in scored:
        key = doc_map.get(c.document_id)
        if key is not None and key not in keys:
            keys.append(key)
    return keys[:limit]


_RANKERS = {"fts": rank_fts, "blend": rank_blend, "fusion": rank_fusion}


# --- scoring ------------------------------------------------------------------------------------

def score_suite(*, limit: int = SEARCH_LIMIT) -> dict:
    """Build the corpus, run every strategy over every query, and return the full scoreboard.

    Offline + deterministic (see module docstring). Callers that must not persist the fixtures
    (the management command) should wrap this in a transaction they roll back; under pytest the
    test transaction rolls back automatically.
    """
    corpus = load_corpus()
    queries = load_queries()
    with fixture_embeddings():
        doc_map = build_corpus(corpus)
        # per-query metric dicts, split overall / by language, for each strategy
        collected = {name: {"all": [], "ar": [], "en": []} for name in STRATEGIES}
        per_query_rows = []
        for q in queries:
            row = {"id": q["id"], "lang": q["lang"]}
            for name in STRATEGIES:
                ranked = _RANKERS[name](q["query"], doc_map, limit=limit)
                scores = metrics.score_query(ranked, q["relevant"])
                collected[name]["all"].append(scores)
                collected[name][q["lang"]].append(scores)
                row[name] = scores
            per_query_rows.append(row)

    strategies = {
        name: {
            "overall": metrics.mean_metrics(buckets["all"]),
            "by_lang": {"ar": metrics.mean_metrics(buckets["ar"]),
                        "en": metrics.mean_metrics(buckets["en"])},
        }
        for name, buckets in collected.items()
    }
    return {
        "corpus_docs": len(corpus),
        "queries": len(queries),
        "queries_ar": sum(1 for q in queries if q["lang"] == "ar"),
        "queries_en": sum(1 for q in queries if q["lang"] == "en"),
        "strategies": strategies,
        "per_query": per_query_rows,
    }


def _delta(a: dict, b: dict) -> dict:
    """``a - b`` per metric (positive = a is better)."""
    return {k: round(a[k] - b[k], 4) for k in a}


def comparison_report(scoreboard: dict) -> dict:
    """The committed baseline-vs-fusion artifact: headline tables + the fusion deltas that T3.3's
    acceptance turns on (fusion must beat the blend baseline, or the gap is investigated)."""
    strat = scoreboard["strategies"]
    fusion, blend, fts = strat["fusion"]["overall"], strat["blend"]["overall"], strat["fts"]["overall"]
    return {
        "suite": "retrieval_v1",
        "offline": True,
        "note": (
            "Fully offline: fixture embeddings are deterministic local bag-of-token vectors "
            "(evals/retrieval.fixture_embed), not live Gemini vectors, and pgvector is off (no "
            "whole-corpus HNSW arm) — the vector arm re-ranks the FTS candidate pool via JSON "
            "cosine. The suite proves the ranking/fusion PIPELINE reproducibly; absolute recall is "
            "bounded by the fixture embedding, not live vectors. Reading the rows: 'fts' is the "
            "pure lexical ceiling; 'fusion' (shipped RRF) equals it here because the crude fixture "
            "cosine adds no lexical signal beyond tsrank and RRF's rank combination preserves the "
            "strong FTS ordering. 'blend' is the removed 0.5*tsrank + 0.5*cosine baseline: it "
            "collapses because that fixture cosine is a noisy signal on a different scale, and "
            "score-blending lets the noise drag true targets out of the top-k — precisely the "
            "score-scale fragility RRF was adopted (T3.2) to remove. So the fusion-over-blend gap "
            "demonstrates RRF's robustness to an incomparable second signal, not a production "
            "recall delta; a high-quality embedding would narrow it."
        ),
        "corpus_docs": scoreboard["corpus_docs"],
        "queries": scoreboard["queries"],
        "queries_ar": scoreboard["queries_ar"],
        "queries_en": scoreboard["queries_en"],
        "strategies": strat,
        "fusion_vs_blend": _delta(fusion, blend),
        "fusion_vs_fts": _delta(fusion, fts),
    }
