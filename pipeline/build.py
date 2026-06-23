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
from .review import get_editor
from .write import get_writer

EDICOES = Path("edicoes")


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
    lines += ["---", "", L["footer"].format(credits=credits)]
    return "\n".join(lines)


def build_edition(top_n: int = 12) -> Path:
    items = collect_all()
    selected = rank(items, top_n=top_n)

    writer, editor = get_writer(), get_editor()
    print(f"\n  Redação: {writer.name}  ·  Revisão: {editor.name}")
    print("-" * 60)

    records: list[dict] = []
    for n, it in enumerate(selected):
        pt, en = writer.write(it)              # 1) draft
        pt, en = editor.review(pt, en, it)     # 2) editorial review
        pt, en = _no_emdash(pt), _no_emdash(en)  # 3) enforce house style
        records.append(
            {
                "title": it.title,
                "url": it.url,
                "source": it.source,
                "kind": it.kind,
                "pt": pt,
                "en": en,
                "score": it.metadata.get("score"),
            }
        )
        print(f"  ✓ [{it.source}] {it.title[:55]}")
        if n < len(selected) - 1:
            time.sleep(1.5)  # stay gentle on the free-tier per-minute limit

    day = date.today().isoformat()
    credits = f"redação {writer.name}, revisão {editor.name}"
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
