"""Writing — draft a short journalistic blurb (PT + EN) for each item.

This is the first of two editorial stages (the second is review.py). With a free
Gemini key the AI drafts the articles following the shared editorial voice;
without one it falls back to extractive mode so the pipeline still produces an
edition (useful for CI and offline runs).
"""

from __future__ import annotations

import os

from .gemini import GEMINI_MODEL, call_gemini, parse_bilingual
from .models import Item
from .style import EDITORIAL_VOICE


class ExtractiveWriter:
    """No-AI fallback: reuse the item's own summary. Free, keyless, offline."""

    name = "extrativo"

    def write(self, item: Item) -> tuple[str, str]:
        body = (item.summary.strip() or item.title)[:500]
        return body, body


class GeminiWriter:
    """Generative writer backed by Google's free-tier Gemini API."""

    name = f"Gemini ({GEMINI_MODEL})"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def write(self, item: Item) -> tuple[str, str]:
        prompt = (
            "You are a tech journalist writing for a weekly tech & science "
            "journal. Write a short blurb about the item below, then revise your "
            "own draft so it fully matches the editorial voice before giving the "
            "final version. Output ONLY the final, polished blurb.\n\n"
            + EDITORIAL_VOICE +
            "\nWrite the SAME blurb in Brazilian Portuguese and English. Return "
            "EXACTLY this format and nothing else:\n"
            "[PT]\n<portuguese text>\n[EN]\n<english text>\n\n"
            f"Source: {item.source}\n"
            f"Title: {item.title}\n"
            f"Context: {item.summary[:800] or '(no extra context)'}\n"
            f"Link: {item.url}\n"
        )
        try:
            return parse_bilingual(call_gemini(self.api_key, prompt))
        except Exception as exc:  # noqa: BLE001 — never let one article kill the run
            print(f"[aviso]   Gemini (redação) falhou em '{item.title[:40]}…': {exc}")
            body = (item.summary.strip() or item.title)[:500]
            return body, body


def get_writer():
    """Pick the best available writer: Gemini if keyed, else extractive."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return GeminiWriter(key)
    print(
        "[aviso] GEMINI_API_KEY ausente — usando modo extrativo (sem IA).\n"
        "        Defina a chave no .env para a IA redigir as matérias."
    )
    return ExtractiveWriter()
