"""Shared edition layout — section labels and grouping.

Used by both the Markdown builder (build.py) and the HTML site (site.py), so the
two renderings always agree on section names and ordering. Each item is a plain
dict (`record`) with at least: title, url, source, kind, pt, en.
"""

from __future__ import annotations

LABELS = {
    "pt": {
        "title": "stdout · Edição de",
        "intro": "Notícias, papers e projetos que movimentaram a semana no mundo "
                 "tech: coletados, ranqueados e redigidos automaticamente.",
        "highlights": "Destaques",
        "papers": "Ciência & Papers",
        "projects": "Projetos em alta",
        "news": "Indústria",
        "footer": "Edição gerada automaticamente por stdout · {credits}.",
    },
    "en": {
        "title": "stdout · Edition of",
        "intro": "The news, papers and projects that moved the tech world this "
                 "week: collected, ranked and written automatically.",
        "highlights": "Highlights",
        "papers": "Science & Papers",
        "projects": "Trending projects",
        "news": "Industry",
        "footer": "Edition generated automatically by stdout · {credits}.",
    },
}


def group_sections(records: list[dict], lang: str) -> list[tuple[str, list[dict]]]:
    """Group records into ordered (heading, items) sections for one language.

    The top 3 (already score-ordered) become Highlights; the rest fall into
    Papers / Projects / Industry by their `kind`.
    """
    L = LABELS[lang]
    highlights, rest = records[:3], records[3:]
    return [
        (L["highlights"], highlights),
        (L["papers"], [r for r in rest if r["kind"] == "paper"]),
        (L["projects"], [r for r in rest if r["kind"] == "project"]),
        (L["news"], [r for r in rest if r["kind"] == "news"]),
    ]
