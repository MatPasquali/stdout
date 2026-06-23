"""Core data model shared across the pipeline.

A single `Item` represents one piece of tech news or one scientific paper,
regardless of where it was collected from. Keeping every source normalised to
the same shape is what lets the ranking and writing stages stay source-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Item:
    title: str
    url: str
    source: str               # human-readable origin, e.g. "Hacker News", "arXiv"
    kind: str                 # "news" | "paper" | "project"
    summary: str = ""
    author: str = ""
    published_at: datetime | None = None
    # Raw popularity signal as reported by the source (HN points, etc.).
    # Sources without a popularity metric leave this at 0.0; the ranking
    # stage is responsible for normalising across sources.
    popularity: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def age_days(self) -> float:
        """How long ago this item was published, in days (0 if unknown)."""
        if self.published_at is None:
            return 0.0
        return (datetime.now(timezone.utc) - self.published_at).total_seconds() / 86400
