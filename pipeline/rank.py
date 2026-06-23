"""Ranking — turn the raw collected pile into a curated, section-aware shortlist.

No AI here: pure heuristics — popularity, recency, topic relevance,
de-duplication and a light anti-spam pass. Then it categorises every item and
picks the best of each section, so Highlights plus every topical section gets
filled. Free, deterministic, fully under our control.
"""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher

from .categorize import categorize
from .layout import SECTION_ORDER
from .models import Item

# Topics the journal favours. A hit in the title/summary adds a small boost, so
# a low-popularity but highly relevant item can still earn a spot.
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
    """Collapse the same story reported by multiple sources into one item."""
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
    # Star-farmed GitHub repos: a pile of stars but no real description.
    return it.kind == "project" and not it.summary.strip()


def rank(items: list[Item], highlights: int = 3, per_section: int = 3,
         highlight_source_cap: int = 2) -> list[Item]:
    """Return Highlights (top overall) plus the top `per_section` of each section."""
    items = _dedup(items)

    # Per-source popularity normalisation, so HN points, GitHub stars and HF
    # likes compare on the same 0..1 scale.
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
        it.metadata["category"] = categorize(it)

    items.sort(key=lambda i: i.metadata["score"], reverse=True)

    chosen: list[Item] = []
    used: set[str] = set()

    # Highlights: top overall, capped per source so the top 3 stay diverse.
    src_count: dict[str, int] = {}
    for it in items:
        if len(chosen) >= highlights:
            break
        if src_count.get(it.source, 0) >= highlight_source_cap:
            continue
        chosen.append(it)
        used.add(it.url)
        src_count[it.source] = src_count.get(it.source, 0) + 1

    # Then the best of each topical section (skipping anything already chosen).
    for cat in SECTION_ORDER:
        count = 0
        for it in items:
            if count >= per_section:
                break
            if it.url in used or it.metadata.get("category") != cat:
                continue
            chosen.append(it)
            used.add(it.url)
            count += 1

    return chosen
