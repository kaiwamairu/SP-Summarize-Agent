"""
backend/scorer.py

Trust Score — rule-based only (no AI calls, zero token cost).

Computes 5 axes per note from frontmatter + source type:
  credibility  — source type prior
  recency      — exponential decay from date_created
  methodology  — placeholder 0.5 (AI enrichment in M6b)
  specificity  — placeholder 0.5 (AI enrichment in M6b)
  consensus    — None (filled by contradictor in M6c)

Writes results back into the note's YAML frontmatter under `trust:`.
Skips notes whose `trust.last_analyzed` >= file mtime (incremental).
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Coroutine

import yaml

from .config import settings

# ── Source-type credibility priors ────────────────────────────────────────────
_CREDIBILITY: dict[str, float] = {
    "paper":  0.90,   # arxiv / peer-reviewed
    "repo":   0.72,   # GitHub — code is verifiable
    "atomic": 0.68,   # synthesized note — depends on source
    "moc":    0.60,   # high-level map — curated but opinionated
    "video":  0.52,   # YouTube — variable quality
}
_CREDIBILITY_DEFAULT = 0.55

# ── Recency decay ─────────────────────────────────────────────────────────────
_RECENCY_HALF_LIFE_DAYS = 730   # score halves every ~2 years


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
    """Replace or prepend YAML frontmatter block in the file."""
    new_fm = yaml.dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    new_block = f"---\n{new_fm}---\n"

    # Remove existing frontmatter
    body = re.sub(r"^---\s*\n.*?\n---\s*\n?", "", text, flags=re.DOTALL)
    path.write_text(new_block + body, encoding="utf-8")


def _calc_recency(date_str: str | None) -> float:
    """Exponential decay: score = 1.0 at today, 0.5 at HALF_LIFE days ago."""
    if not date_str:
        return 0.50
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d").date()
    except ValueError:
        return 0.50
    age_days = (date.today() - d).days
    return round(math.exp(-math.log(2) * age_days / _RECENCY_HALF_LIFE_DAYS), 3)


def _node_type(path: Path) -> str:
    folder_map = {
        "00-MOCs":         "moc",
        "10-Atomic-Notes": "atomic",
        "20-Papers":       "paper",
        "30-Videos":       "video",
        "40-Repos":        "repo",
    }
    return folder_map.get(path.parent.name, "atomic")


def _composite(credibility: float, recency: float,
                methodology: float, specificity: float) -> float:
    """Weighted composite — methodology weighted highest, consensus excluded."""
    weights = dict(credibility=0.30, recency=0.20,
                   methodology=0.30, specificity=0.20)
    raw = (credibility * weights["credibility"] +
           recency     * weights["recency"] +
           methodology * weights["methodology"] +
           specificity * weights["specificity"])
    return round(raw, 3)


def _is_dirty(path: Path, fm: dict[str, Any]) -> bool:
    """True if note needs re-scoring (never scored, or file newer than last_analyzed)."""
    trust = fm.get("trust") or {}
    last_raw = trust.get("last_analyzed")
    if not last_raw:
        return True
    try:
        last_dt = datetime.strptime(str(last_raw), "%Y-%m-%d")
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return mtime > last_dt
    except Exception:
        return True


# ── Public API ────────────────────────────────────────────────────────────────

EmitFn = Callable[[str], Coroutine[Any, Any, None]]


def score_note_sync(path: Path) -> dict[str, Any] | None:
    """
    Score one note. Returns the trust dict written, or None if skipped.
    Modifies the .md file in place (frontmatter only).
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    fm   = _parse_frontmatter(text)

    if not _is_dirty(path, fm):
        return None  # skip — already fresh

    node_type   = _node_type(path)
    credibility = _CREDIBILITY.get(node_type, _CREDIBILITY_DEFAULT)
    recency     = _calc_recency(fm.get("date_created") or fm.get("date"))

    trust = {
        "composite":    _composite(credibility, recency, 0.5, 0.5),
        "credibility":  credibility,
        "recency":      recency,
        "methodology":  0.50,   # placeholder — AI in M6b
        "specificity":  0.50,   # placeholder — AI in M6b
        "consensus":    None,   # filled by contradictor in M6c
        "last_analyzed": date.today().isoformat(),
    }

    fm["trust"] = trust
    _write_frontmatter(path, text, fm)
    return trust


async def score_vault(
    *,
    dry_run: bool = False,
    emit_log: EmitFn,
) -> dict[str, Any]:
    """
    Score all notes in the vault. Incremental — skips unchanged notes.
    Returns summary stats.
    """
    vault = settings.vault_path
    folder_map = {
        "00-MOCs", "10-Atomic-Notes", "20-Papers", "30-Videos", "40-Repos"
    }

    notes = [
        p for p in vault.rglob("*.md")
        if p.parent.name in folder_map
    ]

    updated = skipped = errors = 0

    for path in sorted(notes):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            fm   = _parse_frontmatter(text)

            if not _is_dirty(path, fm):
                skipped += 1
                continue

            if dry_run:
                node_type   = _node_type(path)
                credibility = _CREDIBILITY.get(node_type, _CREDIBILITY_DEFAULT)
                recency     = _calc_recency(fm.get("date_created") or fm.get("date"))
                composite   = _composite(credibility, recency, 0.5, 0.5)
                await emit_log(
                    f"SCORE [DRY] {path.name} -> composite={composite:.2f} "
                    f"(cred={credibility} rec={recency:.2f})"
                )
                updated += 1
            else:
                trust = score_note_sync(path)
                if trust:
                    await emit_log(
                        f"SCORE {path.name} -> {trust['composite']:.2f} "
                        f"(cred={trust['credibility']} rec={trust['recency']:.2f})"
                    )
                    updated += 1

        except Exception as exc:
            await emit_log(f"SCORE [ERR] {path.name}: {exc}")
            errors += 1

    return {"updated": updated, "skipped": skipped, "errors": errors}
