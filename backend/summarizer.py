import os
from typing import Any

from .config import settings
from .ingest.paper import fetch_paper
from .ingest.video import fetch_video
from .ingest.repo import fetch_repo
from .parser import parse_output
from .writer import write_files

_PROMPT_NAMES = {
    "paper": "paper-prompt-v2.txt",
    "video": "video-prompt-v2.txt",
    "repo":  "code-prompt-v2.txt",
}

# Platform-agnostic contract prepended to every prompt.
# Any model that can follow instructions will produce ═══ FILE: ═══ output.
_SYSTEM_PROMPT = """You are a knowledge extraction agent. Your output will be saved directly to an Obsidian PKM vault by an automated parser.

OUTPUT CONTRACT — non-negotiable, parser depends on exact format:

1. Your ENTIRE response must consist ONLY of file sections. No text before, between, or after sections.

2. MANDATORY sections every response must contain (in this order):
   a) ═══ FILE: <filename.md> ═══              ← main note (always required)
   b) ═══ FILE: <name.md> [ATOMIC NOTE] ═══    ← 1-3 atomic notes IF named reusable techniques exist
   c) ═══ FILE: <Topic MOC.md> [MOC — append if exists, create if not] ═══  ← always required

3. The delimiter must be EXACTLY: ═══ FILE: <filename> ═══  (full-width equals signs ═, not regular =)

4. If the source has NO reusable named techniques → skip atomic notes. MOC is still required.

5. NEVER reference an atomic note in frontmatter (atomic_notes:) unless you also output it as a full ═══ FILE: [ATOMIC NOTE] ═══ section below.

Follow all writing rules in the prompt below exactly."""


def _load_prompt(source_type: str) -> str:
    path = settings.prompts_dir / _PROMPT_NAMES[source_type]
    return path.read_text(encoding="utf-8")


def _build_messages(source_type: str, content: str) -> list[dict]:
    """Return OpenAI-style messages list compatible with all three platforms."""
    prompt = _load_prompt(source_type)
    user_content = f"{prompt}\n\n[CONTENT TO SUMMARIZE]\n\n{content}"
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user",   "content": user_content},
    ]


async def fetch_content(job: dict[str, Any]) -> str:
    """Step 1 — Ingest raw content from the source URL."""
    fetch_fn = {"paper": fetch_paper, "video": fetch_video, "repo": fetch_repo}[job["source_type"]]
    return await fetch_fn(job["url"])


async def call_ai_raw(platform: str, model: str, source_type: str, content: str) -> str:
    """Step 2 — Build messages and call the AI platform. Returns raw model output."""
    messages = _build_messages(source_type, content)
    return await _call_ai(platform, model, messages)


async def summarize(job: dict[str, Any]) -> list[dict]:
    """Fetch → AI → parse → write (all-in-one). Returns list of saved file records."""
    content = await fetch_content(job)
    raw = await call_ai_raw(job["platform"], job["model"], job["source_type"], content)
    parsed = parse_output(raw)
    return write_files(parsed, job)


async def _call_ai(platform: str, model: str, messages: list[dict]) -> str:
    if platform == "openrouter":
        return await _call_openrouter(model, messages)
    if platform == "claude":
        return await _call_claude(model, messages)
    if platform == "openai":
        return await _call_openai(model, messages)
    if platform == "gemini":
        return await _call_gemini(model, messages)
    raise ValueError(f"Unknown platform: {platform}")


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
    # Claude uses system separately from messages
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
    # Merge system + user into single turn for Gemini
    combined = "\n\n".join(m["content"] for m in messages)
    gmodel = genai.GenerativeModel(model)
    response = await gmodel.generate_content_async(combined)
    return response.text
