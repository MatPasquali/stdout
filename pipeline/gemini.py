"""Thin wrapper around Google's free-tier Gemini REST API.

Centralises the HTTP call and the bilingual [PT]/[EN] parsing so the writer and
the editor share one implementation. Swapping in another provider later means
touching only this file.
"""

from __future__ import annotations

import os
import re
import time

import requests

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_PT_RE = re.compile(r"\[PT\](.*?)(?:\[EN\]|$)", re.S)
_EN_RE = re.compile(r"\[EN\](.*)$", re.S)


def call_gemini(api_key: str, prompt: str, retry: bool = True) -> str:
    """Single generateContent call. Backs off once on a free-tier 429.

    The key goes in the `x-goog-api-key` header (not the URL) so it can never
    end up in a logged URL, and errors report the status only — never the key.
    """
    resp = requests.post(
        _URL.format(model=GEMINI_MODEL),
        headers={"x-goog-api-key": api_key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600},
        },
        timeout=60,
    )
    if resp.status_code == 429 and retry:
        time.sleep(10)
        return call_gemini(api_key, prompt, retry=False)
    if not resp.ok:
        # Status only — never surface the URL or key in logs.
        raise RuntimeError(f"Gemini API HTTP {resp.status_code}")
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


def parse_bilingual(text: str) -> tuple[str, str]:
    """Split a `[PT]...[EN]...` response into (portuguese, english)."""
    pt_m, en_m = _PT_RE.search(text), _EN_RE.search(text)
    pt = pt_m.group(1).strip() if pt_m else text.strip()
    en = en_m.group(1).strip() if en_m else text.strip()
    return pt, en
