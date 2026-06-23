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


def _retry_delay(resp: requests.Response) -> float | None:
    """Read the server-suggested wait (e.g. 'retryDelay: 38s') from a 429 body."""
    try:
        for detail in resp.json().get("error", {}).get("details", []):
            raw = detail.get("retryDelay", "")
            if raw.endswith("s"):
                return float(raw[:-1])
    except Exception:  # noqa: BLE001 — malformed body just means "no hint"
        pass
    return None


def call_gemini(api_key: str, prompt: str, attempts: int = 5) -> str:
    """Single generateContent call, resilient to free-tier per-minute throttling.

    On a 429 it waits the server-suggested delay (or an exponential backoff) and
    retries, up to `attempts` times. The key goes in the `x-goog-api-key` header
    (not the URL) so it can never leak into a logged URL, and errors report the
    status only — never the key.
    """
    backoff = 8.0
    for attempt in range(attempts):
        resp = requests.post(
            _URL.format(model=GEMINI_MODEL),
            headers={"x-goog-api-key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600},
            },
            timeout=60,
        )
        if resp.status_code == 429 and attempt < attempts - 1:
            time.sleep(min(_retry_delay(resp) or backoff, 65))
            backoff = min(backoff * 2, 60)
            continue
        if not resp.ok:
            # Status only — never surface the URL or key in logs.
            raise RuntimeError(f"Gemini API HTTP {resp.status_code}")
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    raise RuntimeError("Gemini API HTTP 429 (limite por minuto; retries esgotados)")


def parse_bilingual(text: str) -> tuple[str, str]:
    """Split a `[PT]...[EN]...` response into (portuguese, english)."""
    pt_m, en_m = _PT_RE.search(text), _EN_RE.search(text)
    pt = pt_m.group(1).strip() if pt_m else text.strip()
    en = en_m.group(1).strip() if en_m else text.strip()
    return pt, en
