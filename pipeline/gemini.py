"""Thin wrapper around Google's free-tier Gemini REST API.

Kept as a fallback writing provider (Groq is preferred). One HTTP call with a
resilient retry; the key goes in the `x-goog-api-key` header (never the URL), and
errors report the status only, never the key.
"""

from __future__ import annotations

import os
import time

import requests

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _retry_delay(resp: requests.Response) -> float | None:
    """Read the server-suggested wait (e.g. 'retryDelay: 38s') from a 429 body."""
    try:
        for detail in resp.json().get("error", {}).get("details", []):
            raw = detail.get("retryDelay", "")
            if raw.endswith("s"):
                return float(raw[:-1])
    except Exception:  # noqa: BLE001
        pass
    return None


def call_gemini(api_key: str, prompt: str, attempts: int = 5) -> str:
    """Single generateContent call, resilient to free-tier per-minute throttling."""
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
            raise RuntimeError(f"Gemini API HTTP {resp.status_code}")
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    raise RuntimeError("Gemini API HTTP 429 (limite por minuto; retries esgotados)")
