"""
backend/retagger.py

Scan Obsidian vault .md files and enrich their frontmatter tags using AI.

For each file:
  1. Read existing frontmatter + body snippet
  2. Ask AI to suggest richer semantic tags (topic/*, domain/*, method/*, concept/*, framework/*)
  3. Merge new tags into frontmatter (union — never delete existing tags)
  4. Write file back (unless dry_run=True)

Called from POST /api/vault/retag.
"""

import asyncio
import re
from pathlib import Path
from typing import Any, Callable, Awaitable

import yaml

from .config import settings

# ── Folders to retag ──────────────────────────────────────────────────────────
_RETAG_FOLDERS = {"00-MOCs", "10-Atomic-Notes", "20-Papers", "30-Videos", "40-Repos"}

# Tags that should never be removed (identity tags)
_IDENTITY_TAGS = {"paper", "video", "repo", "atomic", "moc", "note", "summarized", "inbox"}

_RETAG_SYSTEM = """You are a knowledge tagging agent for an Obsidian PKM vault.
Your ONLY job: output a YAML list of semantic tags to ADD to a note's frontmatter.

Tag taxonomy — use only these prefixes:
  topic/<subject>       e.g. topic/transformer, topic/reinforcement-learning, topic/llm
  domain/<field>        e.g. domain/nlp, domain/computer-vision, domain/systems
  concept/<idea>        e.g. concept/attention-mechanism, concept/chain-of-thought
  method/<technique>    e.g. method/finetuning, method/rlhf, method/quantization
  framework/<tool>      e.g. framework/pytorch, framework/langchain, framework/electron
  pattern/<design>      e.g. pattern/agent-loop, pattern/rag

Rules:
- Output ONLY a YAML list, nothing else. Example:
  - topic/transformer
  - concept/attention-mechanism
  - domain/nlp
- 3-8 new tags per note. More specific > generic.
- Lowercase, hyphens instead of spaces.
- NEVER repeat tags already in the note.
- NEVER add: paper, video, repo, atomic, moc, summarized, wip, status."""


def _parse_frontmatter_raw(text: str) -> tuple[str, str, str]:
    """Return (before_fm, fm_block, after_fm). fm_block includes the --- delimiters."""
    m = re.match(r"^(---\s*\n)(.*?)(\n---\s*\n)(.*)", text, re.DOTALL)
    if m:
        return "", m.group(1) + m.group(2) + m.group(3), m.group(4)
    return "", "", text  # no frontmatter


def _parse_fm_dict(fm_block: str) -> dict[str, Any]:
    inner = re.sub(r"^---\s*\n|^---\s*$", "", fm_block, flags=re.MULTILINE).strip()
    try:
        data = yaml.safe_load(inner)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _rebuild_frontmatter(fm: dict[str, Any]) -> str:
    """Serialise frontmatter dict back to YAML block with --- delimiters."""
    dumped = yaml.dump(
        fm,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )
    return f"---\n{dumped}---\n"


def _merge_tags(existing: list, new_tags: list[str]) -> list[str]:
    """Union of existing + new tags, preserving order, no duplicates."""
    existing_str = [str(t).strip().lstrip("#").lower() for t in (existing or [])]
    existing_set = set(existing_str)
    merged = list(existing_str)
    for t in new_tags:
        t = t.strip().lstrip("- ").lower()
        if t and t not in existing_set:
            merged.append(t)
            existing_set.add(t)
    return merged


def _body_snippet(body: str, max_chars: int = 800) -> str:
    """Return first N chars of note body for AI context."""
    body = re.sub(r"^---.*?---\s*\n", "", body, flags=re.DOTALL)
    return body[:max_chars].strip()


async def _ask_ai_for_tags(
    platform: str,
    model: str,
    note_text: str,
    existing_tags: list[str],
) -> list[str]:
    """Call AI and parse a YAML list of new tags."""
    from .summarizer import _call_ai  # local import to avoid circular

    existing_str = ", ".join(existing_tags) or "(none)"
    snippet = _body_snippet(note_text)
    user_msg = (
        f"Note snippet:\n\n{snippet}\n\n"
        f"Existing tags (do NOT repeat these): {existing_str}\n\n"
        "Output ONLY a YAML list of new tags to add."
    )
    messages = [
        {"role": "system", "content": _RETAG_SYSTEM},
        {"role": "user",   "content": user_msg},
    ]
    raw = await _call_ai(platform, model, messages)
    # Parse the YAML list
    raw = raw.strip()
    # Strip markdown code fences if model wrapped output
    raw = re.sub(r"^```[a-z]*\n?|```$", "", raw, flags=re.MULTILINE).strip()
    try:
        parsed = yaml.safe_load(raw)
        if isinstance(parsed, list):
            return [str(t).strip().lstrip("- ") for t in parsed if t]
    except yaml.YAMLError:
        pass
    # Fallback: grab lines starting with "- "
    lines = [l.lstrip("- ").strip() for l in raw.splitlines() if l.strip().startswith("- ")]
    return lines


async def retag_vault(
    platform: str,
    model: str,
    *,
    dry_run: bool = False,
    emit_log: Callable[[str], Awaitable[None]] | None = None,
) -> dict[str, Any]:
    """
    Main entry: iterate vault files, enrich tags, write back.
    Returns {"updated": N, "skipped": N, "errors": N, "files": [...]}.
    """
    vault = settings.vault_path
    results = {"updated": 0, "skipped": 0, "errors": 0, "files": []}

    md_files = [
        p for p in sorted(vault.rglob("*.md"))
        if p.parent.name in _RETAG_FOLDERS
    ]

    for md_path in md_files:
        rel = str(md_path.relative_to(vault)).replace("\\", "/")
        try:
            text = md_path.read_text(encoding="utf-8", errors="replace")
            _, fm_block, body = _parse_frontmatter_raw(text)
            if not fm_block:
                if emit_log:
                    await emit_log(f"RETAG :: SKIP (no frontmatter) — {rel}")
                results["skipped"] += 1
                results["files"].append({"file": rel, "action": "skipped", "reason": "no frontmatter"})
                continue

            fm = _parse_fm_dict(fm_block)
            existing_tags: list = fm.get("tags", [])
            if isinstance(existing_tags, str):
                existing_tags = [existing_tags]

            # Ask AI for new tags
            if emit_log:
                await emit_log(f"RETAG :: Tagging {rel}")
            new_tags = await _ask_ai_for_tags(platform, model, text, existing_tags)

            if not new_tags:
                results["skipped"] += 1
                results["files"].append({"file": rel, "action": "skipped", "reason": "no new tags"})
                continue

            merged = _merge_tags(existing_tags, new_tags)
            fm["tags"] = merged

            if not dry_run:
                new_fm_block = _rebuild_frontmatter(fm)
                new_text = new_fm_block + body
                await asyncio.to_thread(md_path.write_text, new_text, encoding="utf-8")

            results["updated"] += 1
            results["files"].append({
                "file": rel,
                "action": "dry_run" if dry_run else "updated",
                "added_tags": new_tags,
                "total_tags": len(merged),
            })

        except Exception as exc:
            if emit_log:
                await emit_log(f"RETAG :: [ERR] {rel} — {type(exc).__name__}: {exc}")
            results["errors"] += 1
            results["files"].append({"file": rel, "action": "error", "error": str(exc)})

    return results
