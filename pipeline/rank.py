"""Ranking — turn the raw collected pile into a curated, ordered shortlist.

No AI here: pure heuristics — popularity, recency, topic relevance,
de-duplication and a light anti-spam pass. Free, deterministic, fully under our
control, and exactly the kind of data engineering a portfolio should show off.
"""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher

from .models import Item

# Topics the journal favours. A hit in the title/summary adds a small boost, so
# a low-popularity but highly relevant paper can still earn a spot.
TOPICS = [
    "ai", "artificial intelligence", "llm", "model", "machine learning", "neural",
    "chip", "gpu", "semiconductor", "quantum", "robot", "security", "privacy",
    "open source", "open-source", "space", "physics", "biology", "climate",
    "agent", "research", "dataset", "benchmark", "compiler", "kernel",
]

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _norm_title(title: str) -> str:
    return _NON_ALNUM.sub(" ", title.lower()).strip()


def _dedup(items: list[Item]) -> list[Item]:
    """Collapse the same story reported by multiple sources into one item.

    Keeps the most popular instance (we sort by popularity first).
    """
    kept: list[Item] = []
    seen: list[str] = []
    for it in sorted(items, key=lambda i: i.popularity, reverse=True):
        norm = _norm_title(it.title)
        if any(SequenceMatcher(None, norm, s).ratio() > 0.85 for s in seen):
            continue
        seen.append(norm)
        kept.append(it)
    return kept


def _topic_boost(it: Item) -> float:
    text = f"{it.title} {it.summary}".lower()
    hits = sum(1 for kw in TOPICS if kw in text)
    return min(hits / 4.0, 1.0)


def _looks_like_spam(it: Item) -> bool:
    # Star-farmed GitHub repos tend to surface with a pile of stars but no real
    # description. That's the `Cowart`-style noise we want to bury.
    return it.kind == "project" and not it.summary.strip()


def rank(items: list[Item], top_n: int = 12, per_source_cap: int = 4) -> list[Item]:
    """Return the top `top_n` items, scored and capped for source diversity."""
    items = _dedup(items)

    # Per-source popularity normalisation, so HN points and GitHub stars compare
    # on the same 0..1 scale (and sources without a metric simply score 0 here).
    max_pop: dict[str, float] = {}
    for it in items:
        max_pop[it.source] = max(max_pop.get(it.source, 0.0), it.popularity)

    for it in items:
        ceiling = max_pop.get(it.source, 0.0)
        pop_norm = math.log1p(it.popularity) / math.log1p(ceiling) if ceiling > 0 else 0.0
        recency = max(0.0, 1.0 - it.age_days / 7.0)
        topic = _topic_boost(it)

        score = 0.5 * pop_norm + 0.3 * recency + 0.2 * topic
        if _looks_like_spam(it):
            score *= 0.1
        it.metadata["score"] = round(score, 4)

    items.sort(key=lambda i: i.metadata["score"], reverse=True)

    # Cap items per source so one feed can't dominate the edition.
    chosen: list[Item] = []
    per_source: dict[str, int] = {}
    for it in items:
        if per_source.get(it.source, 0) >= per_source_cap:
            continue
        per_source[it.source] = per_source.get(it.source, 0) + 1
        chosen.append(it)
        if len(chosen) >= top_n:
            break
    return chosen
