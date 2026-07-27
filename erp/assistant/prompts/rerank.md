---
id: rerank
version: 1.0.0
changelog:
  - "1.0.0: initial version (ai-reliability T3.5)"
---
You are scoring how well retrieved passages answer a search query, for an Egyptian business
ERP's knowledge base. Score each passage independently and skeptically — passage order and
length must not bias you, only whether it actually answers the query.

Query: {query}

Passages (numbered):
{excerpts}

For EVERY passage listed above, score how well it answers the query: 0 (irrelevant), 1 (loosely
related), 2 (relevant), 3 (directly answers it). Respond with a single JSON object only, no prose:
{{"scores": [{{"i": 0, "score": 0}}, ...]}}
