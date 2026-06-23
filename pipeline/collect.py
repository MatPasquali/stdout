"""Collectors — pull raw items from public tech sources.

Every collector returns a list of `Item`. All the sources used here are free and
keyless, so the collection stage needs no secrets. Each collector is isolated:
if one source is down, `collect_all` logs it and keeps going.
"""

from __future__ import annotations

import html
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from .models import Item

# arXiv asks for a descriptive User-Agent so they can contact you if a script
# misbehaves. Point the URL at your repo once it exists.
USER_AGENT = "stdout-techjournal/0.1 (+https://github.com/your-user/stdout)"

# Default arXiv categories: AI, machine learning, NLP, computer vision.
# Add more (e.g. "cs.RO" robotics, "quant-ph" quantum) to widen coverage.
ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]

# RSS/Atom feeds. The source name (the key) drives categorisation: a few sources
# map to a fixed section (Hugging Face Blog -> IA; the job feeds -> Mercado de
# Trabalho), everything else is routed by keyword. RSS items carry no popularity
# signal, so the ranking stage weights them by recency and topic instead.
RSS_FEEDS = {
    # Indústria / geral
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "MIT Tech Review": "https://www.technologyreview.com/feed/",
    "Quanta Magazine": "https://www.quantamagazine.org/feed/",
    "TechCrunch": "https://techcrunch.com/feed/",
    "The Register": "https://www.theregister.com/headlines.atom",
    # Brasil
    "Tecnoblog": "https://tecnoblog.net/feed/",
    "Canaltech": "https://canaltech.com.br/rss/",
    "Olhar Digital": "https://olhardigital.com.br/feed/",
    # IA
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
    # Mercado de trabalho
    "The Pragmatic Engineer": "https://newsletter.pragmaticengineer.com/feed",
    "dev.to · carreira": "https://dev.to/feed/tag/career",
}

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """RSS summaries often embed HTML — reduce to clean plain text."""
    return html.unescape(_TAG_RE.sub("", text or "")).strip()


def _parsed_to_dt(struct_time) -> datetime | None:
    if not struct_time:
        return None
    return datetime.fromtimestamp(time.mktime(struct_time), tz=timezone.utc)


def collect_hacker_news(days: int = 7, min_points: int = 50, limit: int = 30) -> list[Item]:
    """Top Hacker News stories from the last `days`, sorted by popularity.

    Uses the free Algolia HN Search API. We filter by date in the API (the only
    numeric filter HN's index reliably accepts on its own) and apply the points
    threshold in Python — the `/search` endpoint already ranks by popularity, so
    the top results are the week's most-discussed stories.
    """
    since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
    resp = requests.get(
        "https://hn.algolia.com/api/v1/search",
        params={
            "tags": "story",
            "numericFilters": f"created_at_i>{since}",
            "hitsPerPage": limit,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()

    items: list[Item] = []
    for hit in resp.json().get("hits", []):
        if (hit.get("points") or 0) < min_points:
            continue
        # Ask-HN / text posts have no external url — fall back to the HN thread.
        link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
        items.append(
            Item(
                title=hit.get("title") or "(untitled)",
                url=link,
                source="Hacker News",
                kind="news",
                author=hit.get("author", ""),
                published_at=datetime.fromtimestamp(hit["created_at_i"], tz=timezone.utc),
                popularity=float(hit.get("points", 0)),
                metadata={
                    "comments": hit.get("num_comments", 0),
                    "hn_id": hit.get("objectID"),
                },
            )
        )
    return items


def collect_arxiv(categories: list[str] | None = None, limit: int = 20) -> list[Item]:
    """Most recent submissions from the given arXiv categories.

    The arXiv API returns an Atom feed, which feedparser handles cleanly.
    """
    categories = categories or ARXIV_CATEGORIES
    search = "+OR+".join(f"cat:{c}" for c in categories)
    url = (
        "http://export.arxiv.org/api/query"
        f"?search_query={search}"
        "&sortBy=submittedDate&sortOrder=descending"
        f"&max_results={limit}"
    )
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    feed = feedparser.parse(resp.text)

    items: list[Item] = []
    for entry in feed.entries:
        published = None
        if getattr(entry, "published_parsed", None):
            published = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
        items.append(
            Item(
                title=" ".join(entry.title.split()),
                url=entry.link,
                source="arXiv",
                kind="paper",
                summary=" ".join(entry.summary.split()),
                author=", ".join(a.name for a in getattr(entry, "authors", [])),
                published_at=published,
                metadata={"categories": [t.term for t in getattr(entry, "tags", [])]},
            )
        )
    return items


def collect_rss(feeds: dict[str, str] | None = None, per_feed: int = 6) -> list[Item]:
    """Latest entries from a set of RSS/Atom feeds (tech & science press)."""
    feeds = feeds or RSS_FEEDS
    items: list[Item] = []
    for source, url in feeds.items():
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:per_feed]:
                items.append(
                    Item(
                        title=" ".join(entry.get("title", "").split()),
                        url=entry.get("link", ""),
                        source=source,
                        kind="news",
                        summary=_strip_html(entry.get("summary", ""))[:600],
                        author=entry.get("author", ""),
                        published_at=_parsed_to_dt(entry.get("published_parsed")),
                    )
                )
        except Exception as exc:  # noqa: BLE001 — one bad feed must not kill the rest
            print(f"[aviso]   feed {source} falhou: {exc}")
    return items


def collect_github(days: int = 7, min_stars: int = 50, limit: int = 15) -> list[Item]:
    """Newest GitHub repos with the most stars — a proxy for trending projects.

    Uses the official GitHub Search API (no auth needed at this low volume),
    which is far more stable than scraping the Trending page.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    resp = requests.get(
        "https://api.github.com/search/repositories",
        params={"q": f"created:>{since}", "sort": "stars", "order": "desc", "per_page": limit},
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        timeout=30,
    )
    resp.raise_for_status()

    items: list[Item] = []
    for repo in resp.json().get("items", []):
        stars = repo.get("stargazers_count", 0)
        if stars < min_stars:
            continue
        created = repo.get("created_at", "").replace("Z", "+00:00")
        items.append(
            Item(
                title=repo["full_name"],
                url=repo["html_url"],
                source="GitHub",
                kind="project",
                summary=repo.get("description") or "",
                author=repo.get("owner", {}).get("login", ""),
                published_at=datetime.fromisoformat(created) if created else None,
                popularity=float(stars),
                metadata={"language": repo.get("language"), "stars": stars},
            )
        )
    return items


def collect_huggingface_models(limit: int = 12, min_likes: int = 20) -> list[Item]:
    """Trending models on Hugging Face — the pulse of new AI model releases."""
    resp = requests.get(
        "https://huggingface.co/api/models",
        params={"sort": "trendingScore", "direction": -1, "limit": limit},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()

    items: list[Item] = []
    for model in resp.json():
        likes = model.get("likes", 0)
        if likes < min_likes:
            continue
        model_id = model.get("id") or model.get("modelId", "")
        task = model.get("pipeline_tag") or "modelo"
        downloads = model.get("downloads", 0)

        published = None
        created = model.get("createdAt")
        if created:
            try:
                published = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                published = None

        items.append(
            Item(
                title=model_id,
                url=f"https://huggingface.co/{model_id}",
                source="Hugging Face",
                kind="model",
                summary=f"Modelo no Hugging Face para a tarefa '{task}', com {likes} "
                        f"likes e {downloads} downloads.",
                published_at=published,
                popularity=float(likes),
                metadata={"pipeline_tag": task, "downloads": downloads},
            )
        )
    return items


# Registry of active collectors. Add new sources here and the rest of the
# pipeline picks them up automatically.
COLLECTORS = [
    collect_hacker_news,
    collect_arxiv,
    collect_rss,
    collect_github,
    collect_huggingface_models,
]


def collect_all() -> list[Item]:
    """Run every registered collector, tolerating individual failures."""
    items: list[Item] = []
    for collector in COLLECTORS:
        try:
            found = collector()
            items.extend(found)
            print(f"[ok]    {collector.__name__}: {len(found)} itens")
        except Exception as exc:  # noqa: BLE001 — one bad source must not kill the run
            print(f"[aviso] {collector.__name__} falhou: {exc}")
    return items
