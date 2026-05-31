"""
backend/extractor.py

Claim Extraction — M6b

Reads each vault .md note and uses AI to extract factual claims.
Saves a sidecar <stem>.claims.json next to the .md file.
Updates frontmatter with claims_count + claims_last_analyzed.

Sidecar format:
{
  "note":          "2023-gpt4",
  "file":          "20-Papers/2023-gpt4.md",
  "last_analyzed": "2025-06-01",
  "claims": [
    {
      "id":         "c001",
      "text":       "GPT-4 achieves human-level performance on professional exams.",
      "type":       "finding",        # finding | claim | method | comparison | definition
      "confidence": 0.9,             # 0.9=explicit, 0.7=implied, 0.5=uncertain
      "keywords":   ["gpt-4", "benchmark", "performance"]
    }
  ]
}

Frontmatter patch (written back to the .md):
  claims_count:         12
  claims_last_analyzed: 2025-06-01
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Coroutine

import yaml

from .config import settings
from .llm import call_ai

# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a precise claim-extraction engine. "
    "Extract factual claims from the note provided. "
    "Output ONLY a JSON array — no prose, no markdown fences. "
    "If nothing is extractable, output []."
)

_USER_TMPL = """\
Extract the 8-12 most important, verifiable claims from this note.

Each claim object must have:
  "id"         : "c001" … "c099" (zero-padded sequential)
  "text"       : one declarative sentence ≤ 25 words
  "type"       : one of: finding | claim | method | comparison | definition
  "confidence" : 0.9=explicitly stated, 0.7=implied/paraphrased, 0.5=uncertain
  "keywords"   : 2-5 lowercase key terms (list of strings)

Skip: section headings, meta-commentary, trivial background, personal notes.

NOTE CONTENT:
{content}"""

# Maximum chars to feed to the model — keeps token cost low
_MAX_CHARS = 6000

# ── Helpers ───────────────────────────────────────────────────────────────────

EmitFn = Callable[[str], Coroutine[Any, Any, None]]

_FOLDER_MAP = {
    "00-MOCs", "10-Atomic-Notes", "20-Papers", "30-Videos", "40-Repos"
}


def _parse_frontmatter(text: str) -> dict[str, Any]:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _write_frontmatter(path: Path, text: str, fm: dict[str, Any]) -> None:
    new_fm = yaml.dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    new_block = f"---\n{new_fm}---\n"
    body = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", text, flags=re.DOTALL)
    path.write_text(new_block + body, encoding="utf-8")


def _sidecar_path(md_path: Path) -> Path:
    return md_path.with_suffix(".claims.json")


def _is_dirty(md_path: Path, fm: dict[str, Any]) -> bool:
    """True if claims need re-extraction (never extracted, or .md newer than sidecar)."""
    sidecar = _sidecar_path(md_path)
    if not sidecar.exists():
        return True
    last_raw = fm.get("claims_last_analyzed")
    if not last_raw:
        return True
    try:
        last_dt = datetime.strptime(str(last_raw), "%Y-%m-%d")
        mtime   = datetime.fromtimestamp(md_path.stat().st_mtime)
        return mtime > last_dt
    except Exception:
        return True


def _strip_body(text: str) -> str:
    """Remove frontmatter and truncate to _MAX_CHARS."""
    body = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", text, flags=re.DOTALL).strip()
    return body[:_MAX_CHARS]


def _parse_claims(raw: str) -> list[dict]:
    """Parse AI response → validated list of claim dicts."""
    # Strip markdown fences if model forgot the instruction
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Attempt to extract a JSON array from inside larger text
        m = re.search(r"\[[\s\S]*\]", raw)
        if not m:
            return []
        try:
            data = json.loads(m.group())
        except json.JSONDecodeError:
            return []

    if not isinstance(data, list):
        return []

    valid = []
    allowed_types = {"finding", "claim", "method", "comparison", "definition"}
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        cid = str(item.get("id") or f"c{i+1:03d}")
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        ctype = str(item.get("type", "claim")).lower()
        if ctype not in allowed_types:
            ctype = "claim"
        conf = float(item.get("confidence", 0.7))
        conf = max(0.0, min(1.0, conf))
        kw = item.get("keywords", [])
        keywords = [str(k).lower() for k in (kw if isinstance(kw, list) else [])][:5]
        valid.append({
            "id": cid,
            "text": text,
            "type": ctype,
            "confidence": conf,
            "keywords": keywords,
        })
    return valid[:15]  # hard cap — no note needs more than 15 claims


# ── Public API ────────────────────────────────────────────────────────────────

async def extract_note(
    path: Path,
    platform: str,
    model: str,
) -> dict[str, Any] | None:
    """
    Extract claims for one note.
    Returns the saved sidecar dict, or None if skipped (not dirty).
    Writes sidecar .claims.json and patches frontmatter.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    fm   = _parse_frontmatter(text)

    if not _is_dirty(path, fm):
        return None  # already fresh

    body = _strip_body(text)
    if len(body) < 80:
        return None  # too short to extract from

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user",   "content": _USER_TMPL.format(content=body)},
    ]

    raw    = await call_ai(platform, model, messages)
    claims = _parse_claims(raw)

    today = date.today().isoformat()
    vault = settings.vault_path
    rel   = str(path.relative_to(vault)).replace("\\", "/")

    sidecar_data: dict[str, Any] = {
        "note":          path.stem,
        "file":          rel,
        "last_analyzed": today,
        "claims":        claims,
    }

    # Write sidecar
    _sidecar_path(path).write_text(
        json.dumps(sidecar_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Patch frontmatter
    fm["claims_count"]         = len(claims)
    fm["claims_last_analyzed"] = today
    _write_frontmatter(path, text, fm)

    return sidecar_data


async def extract_vault(
    platform: str,
    model: str,
    *,
    dry_run: bool = False,
    emit_log: EmitFn,
) -> dict[str, Any]:
    """
    Run claim extraction over all vault notes.
    Incremental — skips notes with a fresh sidecar.
    Returns summary stats.
    """
    vault = settings.vault_path
    notes = [
        p for p in vault.rglob("*.md")
        if p.parent.name in _FOLDER_MAP
    ]

    extracted = skipped = errors = 0

    for path in sorted(notes):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            fm   = _parse_frontmatter(text)

            if not _is_dirty(path, fm):
                skipped += 1
                continue

            if dry_run:
                await emit_log(f"EXTRACT [DRY] {path.name} -> would extract claims")
                extracted += 1
                continue

            await emit_log(f"EXTRACT {path.name} -> calling {platform}/{model}...")
            result = await extract_note(path, platform, model)

            if result is None:
                skipped += 1
            else:
                cnt = len(result["claims"])
                await emit_log(f"EXTRACT {path.name} -> {cnt} claim(s) saved")
                extracted += 1

        except Exception as exc:
            await emit_log(f"EXTRACT [ERR] {path.name}: {exc}")
            errors += 1

    return {"extracted": extracted, "skipped": skipped, "errors": errors}


def load_claims(note_stem: str) -> dict[str, Any] | None:
    """
    Load the sidecar claims for a note by stem name.
    Searches across all vault folders. Returns None if not found.
    """
    vault = settings.vault_path
    for path in vault.rglob(f"{note_stem}.claims.json"):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None
