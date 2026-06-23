"""Categorisation — decide which section each item belongs to.

Topical sections (IA / Indústria / Mercado de Trabalho) are derived here, with no
AI and no cost: a deterministic pass over source + kind + keywords (PT and EN).
Papers and projects keep their own sections by `kind`.
"""

from __future__ import annotations

import re

from .models import Item

# Sources that always map to a fixed section, regardless of content.
HF_SOURCES = {"Hugging Face", "Hugging Face Blog"}        # -> IA
JOB_SOURCES = {"The Pragmatic Engineer", "dev.to · carreira"}  # -> Mercado de Trabalho

# Job-market signals (checked first: a layoff at an AI company is job-market news).
JOB_WORDS = [
    "hiring", "hire", "hires", "layoff", "layoffs", "fired", "job", "jobs",
    "salary", "salaries", "recruiter", "recruiting", "recruitment", "workforce",
    "career", "careers", "freelance", "freelancer",
    "vaga", "vagas", "salário", "salários", "salario", "carreira", "carreiras",
    "emprego", "empregos", "contratação", "contratações", "contratacao",
    "demissão", "demissões", "demissao", "recrutamento", "estágio", "estagio",
]
JOB_PHRASES = [
    "job market", "mercado de trabalho", "remote work", "trabalho remoto",
    "tech jobs", "return to office", "home office", "mercado tech",
]

# AI signals.
AI_WORDS = [
    "ai", "a.i.", "llm", "llms", "gpt", "gemini", "claude", "llama", "mistral",
    "openai", "anthropic", "transformer", "transformers", "diffusion", "chatbot",
    "agi", "ia",
]
AI_PHRASES = [
    "artificial intelligence", "inteligência artificial", "inteligencia artificial",
    "machine learning", "aprendizado de máquina", "deep learning", "rede neural",
    "neural network", "language model", "modelo de linguagem", "hugging face",
    "generative ai", "ia generativa", "modelo de ia", "large language model",
]


def _matches(text: str, words: list[str], phrases: list[str]) -> bool:
    if any(p in text for p in phrases):
        return True
    return any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words)


def categorize(item: Item) -> str:
    """Return the section key for an item: ia | industria | trabalho | papers | projetos."""
    if item.kind == "paper":
        return "papers"
    if item.kind == "project":
        return "projetos"
    if item.kind == "model" or item.source in HF_SOURCES:
        return "ia"
    if item.source in JOB_SOURCES:
        return "trabalho"

    text = f"{item.title}  {item.summary}".lower()
    if _matches(text, JOB_WORDS, JOB_PHRASES):
        return "trabalho"
    if _matches(text, AI_WORDS, AI_PHRASES):
        return "ia"
    return "industria"
