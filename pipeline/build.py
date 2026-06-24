"""Build a full edition: collect -> rank -> write -> review -> Markdown + JSON.

Writes three things under `edicoes/<date>/`:
  * edition.json   — structured data, consumed by the site generator
  * index.pt.md    — human-readable Markdown (PT)
  * index.en.md    — human-readable Markdown (EN)
"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

from .collect import collect_all
from .layout import LABELS, group_sections
from .rank import rank
from .write import get_writer

EDICOES = Path("edicoes")


def _recent_urls(keep: int = 7) -> set[str]:
    """URLs published in recent editions, for cross-edition de-duplication.

    Today's edition is excluded, so re-running on the same day still produces a
    full edition instead of an empty one.
    """
    today = date.today().isoformat()
    files = [f for f in sorted(EDICOES.glob("*/edition.json"), reverse=True)
             if f.parent.name != today][:keep]
    urls: set[str] = set()
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — a malformed past edition shouldn't block today's
            continue
        urls.update(i.get("url") for i in data.get("items", []))
    return urls


def _no_emdash(text: str) -> str:
    """House style: no em-dashes or en-dashes, whatever the model returns.

    Spaced dashes become commas; a bare en-dash (number ranges) becomes a hyphen.
    """
    text = text.replace(" — ", ", ").replace(" – ", ", ")
    text = text.replace("—", ", ").replace("–", "-")
    return text


def _render_md(records: list[dict], lang: str, day: str, credits: str) -> str:
    L = LABELS[lang]
    lines = [f"# {L['title']} {day}", "", f"_{L['intro']}_", ""]
    for heading, group in group_sections(records, lang):
        if not group:
            continue
        lines += [f"## {heading}", ""]
        for r in group:
            lines += [f"### [{r['title']}]({r['url']})", f"`{r['source']}`", "", r[lang], ""]

    # References — explicit attribution of every source used in the edition.
    lines += [f"## {L['references']}", ""]
    for i, r in enumerate(records, 1):
        lines.append(f"{i}. [{r['title']}]({r['url']}) · `{r['source']}`")

    lines += ["", "---", "", L["footer"].format(credits=credits)]
    return "\n".join(lines)


def build_edition() -> Path:
    items = collect_all()
    seen = _recent_urls()
    fresh = [it for it in items if it.url not in seen]
    print(f"  dedup entre edições: {len(items) - len(fresh)} já publicados removidos")
    selected = rank(fresh)

    writer = get_writer()
    print(f"\n  Redação (com auto-revisão): {writer.name}")
    print("-" * 60)

    records: list[dict] = []
    for n, it in enumerate(selected):
        pt, en = writer.write(it)                # redige e se auto-revisa (1 chamada)
        pt, en = _no_emdash(pt), _no_emdash(en)  # impõe o estilo da casa (sem travessão)
        records.append(
            {
                "title": it.title,
                "url": it.url,
                "source": it.source,
                "kind": it.kind,
                "category": it.metadata.get("category", "industria"),
                "pt": pt,
                "en": en,
                "score": it.metadata.get("score"),
            }
        )
        print(f"  ✓ [{it.source}] {it.title[:55]}")
        if n < len(selected) - 1:
            # ~4s/call keeps us under the free-tier limit (20 req/min) without
            # bursting; the retry in gemini.py absorbs the occasional overshoot.
            time.sleep(4.0)

    day = date.today().isoformat()
    credits = f"redação {writer.name}"
    out = EDICOES / day
    out.mkdir(parents=True, exist_ok=True)
    (out / "edition.json").write_text(
        json.dumps({"date": day, "credits": credits, "items": records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "index.pt.md").write_text(_render_md(records, "pt", day, credits), encoding="utf-8")
    (out / "index.en.md").write_text(_render_md(records, "en", day, credits), encoding="utf-8")
    print(f"\n  Edição salva em {out}")
    return out
