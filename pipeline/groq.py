"""Thin wrapper around Groq's free-tier API (OpenAI-compatible chat completions).

Groq's free tier is far more generous than Gemini's (roughly 30 requests/minute
and ~1,000/day on the 70B model), so a full edition generates reliably. Same role
as gemini.py: one HTTP call with a resilient retry, key only in the header.
"""

from __future__ import annotations

import os
import time

import requests

# llama-3.3-70b-versatile writes the best prose on the free tier. Override with
# GROQ_MODEL (e.g. "llama-3.1-8b-instant" for higher limits and more speed).
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
_URL = "https://api.groq.com/openai/v1/chat/completions"


def call_groq(api_key: str, prompt: str, attempts: int = 4) -> str:
    """Single chat completion, resilient to 429 (honours the retry-after header)."""
    backoff = 5.0
    for attempt in range(attempts):
        resp = requests.post(
            _URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 600,
                # Penalise repetition so a confusing/foreign input can't send the
                # model into a degenerate loop (e.g. "Fang Fang Fang...").
                "frequency_penalty": 0.6,
                "presence_penalty": 0.3,
            },
            timeout=60,
        )
        if resp.status_code == 429 and attempt < attempts - 1:
            try:
                wait = float(resp.headers.get("retry-after", ""))
            except ValueError:
                wait = backoff
            time.sleep(min(wait, 30))
            backoff = min(backoff * 2, 30)
            continue
        if not resp.ok:
            # Status only — never surface the key.
            raise RuntimeError(f"Groq API HTTP {resp.status_code}")
        return resp.json()["choices"][0]["message"]["content"]
    raise RuntimeError("Groq API HTTP 429 (retries esgotados)")
