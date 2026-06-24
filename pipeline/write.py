"""Writing — draft a short journalistic blurb (PT + EN) for each item.

The provider is swappable behind a tiny interface:

* `GroqWriter`      — generative AI via Groq's free tier (preferred: generous limits).
* `GeminiWriter`    — generative AI via Google's free-tier Gemini (fallback).
* `ExtractiveWriter`— no key, no AI: reuses the item's own summary (offline / CI).

`get_writer()` prefers Groq, then Gemini, then extractive. All three share the
same prompt and the same [PT]/[EN] parser, so swapping providers is transparent.
"""

from __future__ import annotations

import os
import re

from .gemini import GEMINI_MODEL, call_gemini
from .groq import GROQ_MODEL, call_groq
from .models import Item
from .style import EDITORIAL_VOICE

_PT_RE = re.compile(r"\[PT\](.*?)(?:\[EN\]|$)", re.S)
_EN_RE = re.compile(r"\[EN\](.*)$", re.S)


def parse_bilingual(text: str) -> tuple[str, str]:
    """Split a `[PT]...[EN]...` response into (portuguese, english)."""
    pt_m, en_m = _PT_RE.search(text), _EN_RE.search(text)
    pt = pt_m.group(1).strip() if pt_m else text.strip()
    en = en_m.group(1).strip() if en_m else text.strip()
    return pt, en


def _build_prompt(item: Item) -> str:
    return (
        "You are a tech journalist writing for a weekly tech & science journal. "
        "Write a short blurb about the item below, then revise your own draft so "
        "it fully matches the editorial voice before giving the final version. "
        "Output ONLY the final, polished blurb.\n"
        "If the source content is in another language (for example Chinese), "
        "translate and summarise its meaning. Never repeat the same word or "
        "phrase; if the content is unclear, write one plain sentence describing "
        "the item based on its title.\n\n" + EDITORIAL_VOICE +
        "\nWrite the SAME blurb in Brazilian Portuguese and English. Return "
        "EXACTLY this format and nothing else:\n"
        "[PT]\n<portuguese text>\n[EN]\n<english text>\n\n"
        f"Source: {item.source}\n"
        f"Title: {item.title}\n"
        f"Context: {item.summary[:800] or '(no extra context)'}\n"
        f"Link: {item.url}\n"
    )


def _fallback(item: Item) -> tuple[str, str]:
    body = (item.summary.strip() or item.title)[:500]
    return body, body


def _looks_degenerate(text: str) -> bool:
    """Detect a repetition loop (e.g. 'Fang Fang Fang...') by low word diversity."""
    words = text.split()
    if len(words) < 12:
        return False
    unique_ratio = len(set(w.lower() for w in words)) / len(words)
    return unique_ratio < 0.35


def _generate(call_fn, api_key: str, item: Item) -> tuple[str, str]:
    """Generate via a provider, retrying once if the output degenerates."""
    prompt = _build_prompt(item)
    for _ in range(2):
        try:
            pt, en = parse_bilingual(call_fn(api_key, prompt))
        except Exception as exc:  # noqa: BLE001 — one failed item must not kill the run
            print(f"[aviso]   IA falhou em '{item.title[:40]}…': {exc}")
            return _fallback(item)
        if not (_looks_degenerate(pt) or _looks_degenerate(en)):
            return pt, en
    print(f"[aviso]   saída degenerada em '{item.title[:40]}…'; usando fallback")
    return _fallback(item)


class ExtractiveWriter:
    """No-AI fallback: reuse the item's own summary. Free, keyless, offline."""

    name = "extrativo"

    def write(self, item: Item) -> tuple[str, str]:
        return _fallback(item)


class GroqWriter:
    """Generative writer backed by Groq's free tier (preferred)."""

    name = f"Groq ({GROQ_MODEL})"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def write(self, item: Item) -> tuple[str, str]:
        return _generate(call_groq, self.api_key, item)


class GeminiWriter:
    """Generative writer backed by Google's free-tier Gemini (fallback)."""

    name = f"Gemini ({GEMINI_MODEL})"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def write(self, item: Item) -> tuple[str, str]:
        return _generate(call_gemini, self.api_key, item)


def get_writer():
    """Prefer Groq, then Gemini, then extractive (no key)."""
    if os.environ.get("GROQ_API_KEY"):
        return GroqWriter(os.environ["GROQ_API_KEY"])
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiWriter(os.environ["GEMINI_API_KEY"])
    print(
        "[aviso] sem GROQ_API_KEY nem GEMINI_API_KEY — usando modo extrativo (sem IA).\n"
        "        Defina uma chave no .env para a IA redigir as matérias."
    )
    return ExtractiveWriter()
