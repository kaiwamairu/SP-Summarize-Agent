"""
backend/llm.py

Thin shared AI-call dispatcher used by extractor, contradictor, and
any future module that needs a raw LLM response without the full
summariser overhead.

Usage:
    from .llm import call_ai
    raw = await call_ai(platform, model, messages)

`messages` follows the OpenAI chat format:
    [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
"""

from __future__ import annotations

import os
from typing import Any

from .config import settings


async def call_ai(platform: str, model: str, messages: list[dict[str, Any]]) -> str:
    """Dispatch to the correct AI backend and return the raw text response."""
    if platform == "openrouter":
        return await _call_openrouter(model, messages)
    if platform == "claude":
        return await _call_claude(model, messages)
    if platform == "openai":
        return await _call_openai(model, messages)
    if platform == "gemini":
        return await _call_gemini(model, messages)
    raise ValueError(f"Unknown platform: {platform!r}")


# ── Backends ──────────────────────────────────────────────────────────────────

async def _call_openrouter(model: str, messages: list[dict]) -> str:
    from openai import AsyncOpenAI
    cfg = settings.platforms["openrouter"]
    client = AsyncOpenAI(
        api_key=os.environ["OPENROUTER_API_KEY"],
        base_url=cfg["base_url"],
    )
    response = await client.chat.completions.create(
        model=model,
        max_tokens=cfg["max_tokens"],
        messages=messages,
        extra_headers={
            "HTTP-Referer": "https://summarize-agent.local",
            "X-Title": "Summarize Agent",
        },
    )
    return response.choices[0].message.content


async def _call_claude(model: str, messages: list[dict]) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    cfg = settings.platforms["claude"]
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user_msgs = [m for m in messages if m["role"] != "system"]
    response = await client.messages.create(
        model=model,
        max_tokens=cfg["max_tokens"],
        system=system,
        messages=user_msgs,
    )
    return response.content[0].text


async def _call_openai(model: str, messages: list[dict]) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    cfg = settings.platforms["openai"]
    response = await client.chat.completions.create(
        model=model,
        max_tokens=cfg["max_tokens"],
        messages=messages,
    )
    return response.choices[0].message.content


async def _call_gemini(model: str, messages: list[dict]) -> str:
    import google.generativeai as genai
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    combined = "\n\n".join(m["content"] for m in messages)
    gmodel = genai.GenerativeModel(model)
    response = await gmodel.generate_content_async(combined)
    return response.text
