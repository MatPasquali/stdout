"""Shared edition layout — section labels, order and grouping.

Used by both the Markdown builder (build.py) and the HTML site (site.py), so the
two renderings always agree. Each item is a plain dict (`record`) with at least:
title, url, source, kind, category, pt, en.
"""

from __future__ import annotations

# Topical sections, in the order they appear (after Highlights). Keys match the
# values returned by `categorize()` and the LABELS keys below.
SECTION_ORDER = ["ia", "industria", "trabalho", "papers", "projetos"]

LABELS = {
    "pt": {
        "title": "stdout · Edição de",
        "intro": "Notícias, papers e projetos que movimentaram a semana no mundo "
                 "tech: coletados, ranqueados e redigidos automaticamente.",
        "highlights": "Destaques",
        "ia": "Inteligência Artificial",
        "industria": "Indústria",
        "trabalho": "Mercado de Trabalho",
        "papers": "Ciência & Papers",
        "projetos": "Projetos em alta",
        "references": "Referências",
        "footer": "Edição gerada automaticamente por stdout · {credits}.",
    },
    "en": {
        "title": "stdout · Edition of",
        "intro": "The news, papers and projects that moved the tech world this "
                 "week: collected, ranked and written automatically.",
        "highlights": "Highlights",
        "ia": "Artificial Intelligence",
        "industria": "Industry",
        "trabalho": "Job Market",
        "papers": "Science & Papers",
        "projetos": "Trending projects",
        "references": "References",
        "footer": "Edition generated automatically by stdout · {credits}.",
    },
}


_KNOWN = set(SECTION_ORDER)


def group_sections(records: list[dict], lang: str) -> list[tuple[str, list[dict]]]:
    """Group records into ordered (heading, items) sections for one language.

    The top 3 (already score-ordered) are Highlights; the rest fall into their
    topical section via the `category` field. Items without a known category
    (e.g. older editions made before categorisation existed) default to Industry,
    so no item is ever silently dropped. Empty sections are skipped by renderers.
    """
    L = LABELS[lang]
    highlights, rest = records[:3], records[3:]
    sections = [(L["highlights"], highlights)]
    for cat in SECTION_ORDER:
        if cat == "industria":
            group = [r for r in rest if r.get("category") not in (_KNOWN - {"industria"})]
        else:
            group = [r for r in rest if r.get("category") == cat]
        sections.append((L[cat], group))
    return sections
