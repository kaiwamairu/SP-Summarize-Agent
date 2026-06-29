"""
backend/mcp_server.py

Summarize MCP Server — Phase 1 (core tools)

Turns the Summarize Agent backend into an MCP server so Claude (Desktop / Code)
can summarize a URL into the Obsidian vault, with **Claude itself** doing the
summarization (no OpenRouter / API key needed).

Pattern: Claude = brain, this server = hands.
  1. fetch_source(url)      → resolve + fetch content + hand back the prompt
  2. (Claude summarizes following the ═══ FILE ═══ contract)
  3. save_summary(markdown) → parse + write notes into the vault
  + list_vault_notes()      → let Claude check for duplicates / find the MOC

Reuses: resolver, summarizer.fetch_content, prompts, parser, writer, config.

Run (stdio transport — Claude Desktop / Code spawn this automatically):
    py -3 -m backend.mcp_server
"""

from __future__ import annotations

import re
from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP

from .config import settings
from .resolver import resolve_url
from .summarizer import fetch_content, _load_prompt, _SYSTEM_PROMPT
from .parser import parse_output
from .writer import write_files

mcp = FastMCP("summarize-agent")

_VAULT_FOLDERS = {"00-MOCs", "10-Atomic-Notes", "20-Papers", "30-Videos", "40-Repos"}


# ── Tool 1: fetch_source ──────────────────────────────────────────────────────

@mcp.tool()
async def fetch_source(url: str) -> dict[str, Any]:
    """Fetch the raw content of a URL and return it with the summarization prompt.

    Supports arxiv papers, YouTube videos, and GitHub repos (auto-detected).
    Content is already truncated to a context-safe size by the ingesters.

    After calling this, YOU (Claude) should:
      1. Read `content` and follow `prompt` + `system_contract`.
      2. Optionally call list_vault_notes() to find the right MOC / avoid dupes.
      3. Produce the summary using the ═══ FILE: <name> ═══ delimiter format.
      4. Call save_summary(markdown, source_type, url) with that output.

    Returns:
      source_type      — "paper" | "video" | "repo"
      url              — echoed back (pass to save_summary)
      content          — the fetched source text
      prompt           — the per-type summarization prompt to follow
      system_contract  — the output-format contract (═══ FILE ═══ rules)
      next_step        — human-readable reminder of what to do next
    """
    source_type = resolve_url(url)
    job = {"url": url, "source_type": source_type}
    content = await fetch_content(job)
    prompt = _load_prompt(source_type)
    return {
        "source_type": source_type,
        "url": url,
        "content": content,
        "prompt": prompt,
        "system_contract": _SYSTEM_PROMPT,
        "next_step": (
            "Summarize `content` by following `prompt` and `system_contract`. "
            "Output ONLY ═══ FILE: <name> ═══ sections, then call "
            "save_summary(markdown=<your output>, source_type="
            f"'{source_type}', url='{url}')."
        ),
    }


# ── Tool 2: save_summary ──────────────────────────────────────────────────────

@mcp.tool()
def save_summary(
    markdown: str,
    source_type: str,
    url: str = "",
    on_conflict: str = "overwrite",
) -> dict[str, Any]:
    """Parse a ═══ FILE ═══ summary and write the notes into the Obsidian vault.

    Args:
      markdown     — full summary output containing ═══ FILE: <name> ═══ sections
      source_type  — "paper" | "video" | "repo" (from fetch_source)
      url          — original source URL (optional, stored for reference)
      on_conflict  — when a non-MOC note already exists:
                       "overwrite" (default) | "skip" | "rename"
                     (MOC files always append.) Check list_vault_notes() first
                     if you want to decide intelligently.

    Returns:
      ok     — True if at least one file was written
      saved  — [{filename, path, file_type, action}] per note
      count  — number of files written
      error  — present only when parsing failed
    """
    if source_type not in {"paper", "video", "repo"}:
        source_type = resolve_url(url) if url else "paper"
    if on_conflict not in {"overwrite", "skip", "rename"}:
        on_conflict = "overwrite"

    parsed = parse_output(markdown)
    if not parsed:
        return {
            "ok": False,
            "error": (
                "No ═══ FILE: <name> ═══ sections found. Make sure the markdown "
                "uses the full-width delimiter exactly: ═══ FILE: <filename.md> ═══"
            ),
            "saved": [],
            "count": 0,
        }

    job = {"url": url, "source_type": source_type}
    saved = write_files(parsed, job, on_conflict=on_conflict)
    return {"ok": True, "saved": saved, "count": len(saved)}


# ── Tool 3: list_vault_notes ──────────────────────────────────────────────────

@mcp.tool()
def list_vault_notes() -> dict[str, Any]:
    """List all notes in the vault — call this before save_summary to check for
    duplicates and find the right MOC to append to.

    Returns:
      notes — [{stem, folder, title, tags}] for every note in the 5 vault folders
      count — total number of notes
    """
    vault = settings.vault_path
    notes: list[dict[str, Any]] = []

    for p in sorted(vault.rglob("*.md")):
        if p.parent.name not in _VAULT_FOLDERS:
            continue
        title, tags = p.stem, []
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
            m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
            if m:
                fm = yaml.safe_load(m.group(1)) or {}
                raw_title = fm.get("title")
                if raw_title:
                    title = str(raw_title).split("|")[-1].strip()
                raw_tags = fm.get("tags", [])
                if isinstance(raw_tags, str):
                    raw_tags = [raw_tags]
                tags = [str(t).strip().lstrip("#") for t in (raw_tags or [])]
        except Exception:
            pass
        notes.append({
            "stem": p.stem,
            "folder": p.parent.name,
            "title": title,
            "tags": tags,
        })

    return {"notes": notes, "count": len(notes)}


# ── Prompt: /summarize (slash command on Claude Desktop) ──────────────────────

@mcp.prompt()
def summarize(url: str) -> str:
    """Summarize a URL (arxiv paper / YouTube video / GitHub repo) into the Obsidian vault."""
    return (
        f"Summarize this source into my Obsidian vault: {url}\n\n"
        "Follow these steps using the summarize-agent tools:\n"
        f"1. Call fetch_source(\"{url}\") to get the content + the summarization prompt.\n"
        "2. Call list_vault_notes() to check for existing related notes and find the "
        "right MOC to append to (avoid duplicates).\n"
        "3. Write the summary by following the returned `prompt` and `system_contract` "
        "EXACTLY — output only ═══ FILE: <name> ═══ sections.\n"
        "4. Call save_summary(markdown=<your output>, source_type=<from step 1>, "
        f"url=\"{url}\", on_conflict=<overwrite|skip|rename>). Pick on_conflict based on "
        "what list_vault_notes showed.\n"
        "5. Report which files were created / updated / appended."
    )


if __name__ == "__main__":
    mcp.run()
