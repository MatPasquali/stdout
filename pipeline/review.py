"""Editorial review — a second AI pass that enforces the house voice.

The writer drafts; the editor rewrites that draft so it fully matches the shared
editorial voice (technical but didactic, conversational, jargon explained). This
is the classic writer -> editor workflow, automated. Without a key it's a no-op,
so the pipeline still runs end to end.
"""

from __future__ import annotations

import os

from .gemini import call_gemini, parse_bilingual
from .models import Item
from .style import EDITORIAL_VOICE


class PassthroughEditor:
    """No-op editor (no key / extractive mode): returns the draft unchanged."""

    name = "nenhuma"

    def review(self, pt: str, en: str, item: Item) -> tuple[str, str]:
        return pt, en


class GeminiEditor:
    """AI editor: revises a draft to fully match the editorial voice."""

    name = "Gemini"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def review(self, pt: str, en: str, item: Item) -> tuple[str, str]:
        prompt = (
            "You are the editor of a tech & science journal. Revise the draft "
            "below so it fully matches the editorial voice. Keep every fact "
            "intact, keep both languages, and do not add information that isn't "
            "in the draft. If a term is technical, make sure it's explained in "
            "plain words.\n\n" + EDITORIAL_VOICE +
            "\nIf the draft already fits perfectly, return it unchanged. Return "
            "EXACTLY this format and nothing else:\n"
            "[PT]\n<portuguese text>\n[EN]\n<english text>\n\n"
            f"Title: {item.title}\n"
            f"Draft:\n[PT]\n{pt}\n[EN]\n{en}\n"
        )
        try:
            return parse_bilingual(call_gemini(self.api_key, prompt))
        except Exception as exc:  # noqa: BLE001 — keep the draft if review fails
            print(f"[aviso]   Gemini (revisão) falhou em '{item.title[:40]}…': {exc}")
            return pt, en


def get_editor():
    """AI editor when a key is present, otherwise a transparent no-op."""
    key = os.environ.get("GEMINI_API_KEY")
    return GeminiEditor(key) if key else PassthroughEditor()
