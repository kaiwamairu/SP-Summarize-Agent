"""
backend/contradictor.py

Contradiction Detector — M6c

Compares claims across notes that share a semantic tag.
Uses AI to identify contradictory pairs — outputs:
  1. Per-note sidecar  <stem>.contradictions.json
  2. Vault-level report  00-MOCs/Contradiction-Report.md

Design:
  - Groups notes by tag (from frontmatter)
  - Within each tag group, builds all note-pairs that both have claims sidecars
  - For each pair, sends both claims lists to AI and asks: "Do any claims contradict?"
  - Contradiction output: list of pairs {claim_a_id, claim_b_id, severity, explanation}
  - Severity: critical | moderate | minor
  - Incremental: skips pairs where neither note has changed since last contradiction check
  - Batch limit: max _MAX_PAIRS_PER_RUN pairs to cap token cost

Contradiction sidecar format (written to each note):
{
  "note": "2023-gpt4",
  "last_checked": "2025-06-01",
  "contradictions": [
    {
      "pair_note":     "2024-llama3",
      "claim_self":    {"id": "c003", "text": "..."},
      "claim_other":   {"id": "c007", "text": "..."},
      "severity":      "moderate",
      "explanation":   "Note A claims X while Note B claims Y."
    }
  ]
}

Frontmatter patch on each note:
  contradiction_count: 2
  contradiction_severity: moderate   # worst severity found
  contradiction_checked: 2025-06-01
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from itertools import combinations
from pathlib import Path
from typing import Any, Callable, Coroutine

import yaml

from .config import settings
from .llm import call_ai

# ── Config ────────────────────────────────────────────────────────────────────

_FOLDER_MAP = {
    "00-MOCs", "10-Atomic-Notes", "20-Papers", "30-Videos", "40-Repos"
}

# Max pairs to check per run (controls token cost)
_MAX_PAIRS_PER_RUN = 40

# Severity ordering for "worst" computation
_SEVERITY_ORDER = {"critical": 3, "moderate": 2, "minor": 1, "none": 0}

# ── Prompts ───────────────────────────────────────────────────────────────────

_SYSTEM = (
    "You are a rigorous claim-comparison engine. "
    "Find factual contradictions between two sets of claims. "
    "Output ONLY a JSON array — no prose, no markdown fences. "
    "Empty array [] if no contradictions found."
)

_USER_TMPL = """\
Compare claims from NOTE_A and NOTE_B. Identify pairs that DIRECTLY contradict each other
(not merely different perspectives or levels of detail).

A contradiction means: claim A states X, claim B states NOT-X (about the same subject).

Output a JSON array of contradiction objects:
  "claim_a_id"  : id from NOTE_A claims
  "claim_b_id"  : id from NOTE_B claims
  "severity"    : "critical" | "moderate" | "minor"
  "explanation" : one sentence explaining the contradiction (≤ 30 words)

Severity guide:
  critical = directly contradicts a factual result (numbers, outcomes)
  moderate = contradicts a method or process description
  minor    = contradicts a framing or emphasis

NOTE_A ({note_a}):
{claims_a}

NOTE_B ({note_b}):
{claims_b}"""

# ── Helpers ───────────────────────────────────────────────────────────────────

EmitFn = Callable[[str], Coroutine[Any, Any, None]]


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
    return md_path.with_suffix(".contradictions.json")


def _claims_sidecar_path(md_path: Path) -> Path:
    return md_path.with_suffix(".claims.json")


def _load_claims(md_path: Path) -> list[dict] | None:
    cp = _claims_sidecar_path(md_path)
    if not cp.exists():
        return None
    try:
        data = json.loads(cp.read_text(encoding="utf-8"))
        return data.get("claims") or []
    except Exception:
        return None


def _is_dirty_pair(path_a: Path, path_b: Path) -> bool:
    """True if the pair needs re-checking."""
    sc = _sidecar_path(path_a)
    if not sc.exists():
        return True
    try:
        data = json.loads(sc.read_text(encoding="utf-8"))
        last_raw = data.get("last_checked")
        if not last_raw:
            return True
        last_dt = datetime.strptime(str(last_raw), "%Y-%m-%d")
        mtime_a = datetime.fromtimestamp(path_a.stat().st_mtime)
        mtime_b = datetime.fromtimestamp(path_b.stat().st_mtime)
        return mtime_a > last_dt or mtime_b > last_dt
    except Exception:
        return True


def _format_claims(claims: list[dict]) -> str:
    return "\n".join(
        f"  [{c['id']}] ({c['type']}, conf={c['confidence']:.1f}) {c['text']}"
        for c in claims[:12]  # limit per note to keep prompt short
    )


def _parse_contradictions(raw: str) -> list[dict]:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
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
    allowed_sev = {"critical", "moderate", "minor"}
    for item in data:
        if not isinstance(item, dict):
            continue
        ca = str(item.get("claim_a_id", "")).strip()
        cb = str(item.get("claim_b_id", "")).strip()
        sev = str(item.get("severity", "minor")).lower()
        if sev not in allowed_sev:
            sev = "minor"
        expl = str(item.get("explanation", "")).strip()
        if ca and cb and expl:
            valid.append({
                "claim_a_id":  ca,
                "claim_b_id":  cb,
                "severity":    sev,
                "explanation": expl,
            })
    return valid


def _worst_severity(contradictions: list[dict]) -> str:
    if not contradictions:
        return "none"
    return max(contradictions, key=lambda c: _SEVERITY_ORDER.get(c["severity"], 0))["severity"]


# ── Core pair check ───────────────────────────────────────────────────────────

async def _check_pair(
    path_a: Path,
    path_b: Path,
    platform: str,
    model: str,
) -> list[dict]:
    """Run contradiction check for one note pair. Returns contradiction list."""
    claims_a = _load_claims(path_a)
    claims_b = _load_claims(path_b)
    if not claims_a or not claims_b:
        return []

    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user",   "content": _USER_TMPL.format(
            note_a    = path_a.stem,
            note_b    = path_b.stem,
            claims_a  = _format_claims(claims_a),
            claims_b  = _format_claims(claims_b),
        )},
    ]
    raw  = await call_ai(platform, model, messages)
    return _parse_contradictions(raw)


# ── Sidecar + frontmatter update ──────────────────────────────────────────────

def _update_sidecar(md_path: Path, new_entries: list[dict]) -> None:
    """Merge new contradiction entries into the note's sidecar file."""
    sc = _sidecar_path(md_path)
    today = date.today().isoformat()

    # Load existing sidecar or create fresh
    existing: dict[str, Any] = {"note": md_path.stem, "last_checked": today, "contradictions": []}
    if sc.exists():
        try:
            existing = json.loads(sc.read_text(encoding="utf-8"))
        except Exception:
            pass

    existing["last_checked"] = today

    # Merge: keep existing entries for pairs NOT in new_entries, add new
    new_pair_notes = {e["pair_note"] for e in new_entries}
    kept = [c for c in existing.get("contradictions", [])
            if c.get("pair_note") not in new_pair_notes]
    existing["contradictions"] = kept + new_entries

    sc.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


def _patch_frontmatter(md_path: Path, contradictions: list[dict]) -> None:
    text = md_path.read_text(encoding="utf-8", errors="replace")
    fm   = _parse_frontmatter(text)

    # Load full sidecar for accurate total count
    sc = _sidecar_path(md_path)
    all_contradictions: list[dict] = []
    if sc.exists():
        try:
            all_contradictions = json.loads(sc.read_text(encoding="utf-8")).get("contradictions", [])
        except Exception:
            pass

    fm["contradiction_count"]    = len(all_contradictions)
    fm["contradiction_severity"] = _worst_severity(all_contradictions)
    fm["contradiction_checked"]  = date.today().isoformat()
    _write_frontmatter(md_path, text, fm)


# ── Public API ────────────────────────────────────────────────────────────────

async def detect_vault(
    platform: str,
    model: str,
    *,
    dry_run: bool = False,
    emit_log: EmitFn,
) -> dict[str, Any]:
    """
    Run contradiction detection across the vault.
    Groups notes by shared tag, checks all pairs within each group.
    Capped at _MAX_PAIRS_PER_RUN total AI calls per run.
    Returns summary stats.
    """
    vault = settings.vault_path

    # ── Step 1: Index notes by tag ────────────────────────────────────────────
    tag_to_notes: dict[str, list[Path]] = {}
    note_paths: dict[str, Path] = {}  # stem -> path

    for path in sorted(vault.rglob("*.md")):
        if path.parent.name not in _FOLDER_MAP:
            continue
        # Only process notes that have claims
        if not _claims_sidecar_path(path).exists():
            continue

        text = path.read_text(encoding="utf-8", errors="replace")
        fm   = _parse_frontmatter(text)
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        tags = [t.strip().lstrip("#").lower() for t in (tags or []) if t]

        note_paths[path.stem] = path
        for tag in tags:
            tag_to_notes.setdefault(tag, []).append(path)

    # ── Step 2: Collect candidate pairs (shared tag, both have claims) ────────
    # Use a set to avoid duplicate pairs
    candidate_pairs: set[frozenset] = set()
    for tag, paths in tag_to_notes.items():
        if len(paths) < 2:
            continue
        for a, b in combinations(paths, 2):
            candidate_pairs.add(frozenset([a, b]))

    # Filter to dirty pairs only
    dirty_pairs = [
        tuple(sorted(pair, key=lambda p: p.stem))  # type: ignore[arg-type]
        for pair in candidate_pairs
        if _is_dirty_pair(*sorted(pair, key=lambda p: p.stem))  # type: ignore[arg-type]
    ]

    await emit_log(
        f"CONTRADICT :: {len(note_paths)} notes with claims, "
        f"{len(candidate_pairs)} pairs, {len(dirty_pairs)} dirty"
    )

    # ── Step 3: Process pairs (up to cap) ─────────────────────────────────────
    checked = skipped = errors = found = 0
    skipped += (len(candidate_pairs) - len(dirty_pairs))  # already-fresh pairs

    for path_a, path_b in dirty_pairs[:_MAX_PAIRS_PER_RUN]:
        try:
            if dry_run:
                await emit_log(
                    f"CONTRADICT [DRY] {path_a.stem} <-> {path_b.stem}"
                )
                checked += 1
                continue

            await emit_log(
                f"CONTRADICT {path_a.stem} <-> {path_b.stem} ..."
            )
            contras = await _check_pair(path_a, path_b, platform, model)
            checked += 1

            if contras:
                found += len(contras)
                await emit_log(
                    f"  -> {len(contras)} contradiction(s) found "
                    f"({', '.join(c['severity'] for c in contras)})"
                )

                # Write sidecar for A (from A's perspective)
                entries_for_a = [
                    {
                        "pair_note":   path_b.stem,
                        "claim_self":  _claim_by_id(_load_claims(path_a) or [], c["claim_a_id"]),
                        "claim_other": _claim_by_id(_load_claims(path_b) or [], c["claim_b_id"]),
                        "severity":    c["severity"],
                        "explanation": c["explanation"],
                    }
                    for c in contras
                ]
                # Write sidecar for B (from B's perspective)
                entries_for_b = [
                    {
                        "pair_note":   path_a.stem,
                        "claim_self":  _claim_by_id(_load_claims(path_b) or [], c["claim_b_id"]),
                        "claim_other": _claim_by_id(_load_claims(path_a) or [], c["claim_a_id"]),
                        "severity":    c["severity"],
                        "explanation": c["explanation"],
                    }
                    for c in contras
                ]

                _update_sidecar(path_a, entries_for_a)
                _update_sidecar(path_b, entries_for_b)
                _patch_frontmatter(path_a, entries_for_a)
                _patch_frontmatter(path_b, entries_for_b)
            else:
                # No contradictions — still update last_checked in frontmatter
                _update_sidecar(path_a, [])
                _update_sidecar(path_b, [])
                _patch_frontmatter(path_a, [])
                _patch_frontmatter(path_b, [])

        except Exception as exc:
            await emit_log(f"CONTRADICT [ERR] {path_a.stem}<->{path_b.stem}: {exc}")
            errors += 1

    # Cap notice
    if len(dirty_pairs) > _MAX_PAIRS_PER_RUN:
        remaining = len(dirty_pairs) - _MAX_PAIRS_PER_RUN
        await emit_log(
            f"CONTRADICT :: Cap reached ({_MAX_PAIRS_PER_RUN} pairs). "
            f"{remaining} pair(s) deferred to next run."
        )

    # ── Step 4: Generate vault-level report ───────────────────────────────────
    if not dry_run and checked > 0:
        try:
            _write_contradiction_report(vault, note_paths)
            await emit_log("CONTRADICT :: Report -> 00-MOCs/Contradiction-Report.md")
        except Exception as exc:
            await emit_log(f"CONTRADICT [WARN] Report write failed: {exc}")

    return {
        "checked":  checked,
        "skipped":  skipped,
        "found":    found,
        "errors":   errors,
    }


def _claim_by_id(claims: list[dict], cid: str) -> dict:
    for c in claims:
        if c.get("id") == cid:
            return {"id": c["id"], "text": c["text"]}
    return {"id": cid, "text": "(claim not found)"}


def _write_contradiction_report(vault: Path, note_paths: dict[str, Path]) -> None:
    """Scan all contradiction sidecars and write a Markdown report to 00-MOCs."""
    today = date.today().isoformat()
    all_contras: list[dict] = []

    for stem, path in note_paths.items():
        sc = _sidecar_path(path)
        if not sc.exists():
            continue
        try:
            data = json.loads(sc.read_text(encoding="utf-8"))
            for entry in data.get("contradictions", []):
                all_contras.append({
                    "note_a": stem,
                    "note_b": entry.get("pair_note", "?"),
                    "severity": entry.get("severity", "minor"),
                    "claim_a_text": (entry.get("claim_self") or {}).get("text", "?"),
                    "claim_b_text": (entry.get("claim_other") or {}).get("text", "?"),
                    "explanation": entry.get("explanation", ""),
                })
        except Exception:
            continue

    # De-duplicate (each pair appears from both sides)
    seen: set[frozenset] = set()
    unique: list[dict] = []
    for c in all_contras:
        key = frozenset([c["note_a"], c["note_b"]])
        if key not in seen:
            seen.add(key)
            unique.append(c)

    # Sort: critical first
    unique.sort(key=lambda x: _SEVERITY_ORDER.get(x["severity"], 0), reverse=True)

    # Severity counts
    counts = {"critical": 0, "moderate": 0, "minor": 0}
    for c in unique:
        counts[c["severity"]] = counts.get(c["severity"], 0) + 1

    lines = [
        "---",
        f"title: Contradiction Report",
        f"date_created: {today}",
        f"tags: [contradiction, audit, moc]",
        f"contradiction_total: {len(unique)}",
        "---",
        "",
        f"# Contradiction Report",
        f"",
        f"Generated: {today} | Total: {len(unique)} pairs",
        f"  Critical: {counts['critical']}  Moderate: {counts['moderate']}  Minor: {counts['minor']}",
        "",
    ]

    if not unique:
        lines.append("> No contradictions detected in current vault.")
    else:
        for sev in ["critical", "moderate", "minor"]:
            batch = [c for c in unique if c["severity"] == sev]
            if not batch:
                continue
            lines.append(f"## {sev.capitalize()} ({len(batch)})")
            lines.append("")
            for c in batch:
                lines.append(f"### [[{c['note_a']}]] vs [[{c['note_b']}]]")
                lines.append(f"- **A:** {c['claim_a_text']}")
                lines.append(f"- **B:** {c['claim_b_text']}")
                lines.append(f"- **Explanation:** {c['explanation']}")
                lines.append("")

    report_path = vault / "00-MOCs" / "Contradiction-Report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")


def load_contradictions(note_stem: str) -> dict[str, Any] | None:
    """Load contradiction sidecar for a note by stem. Returns None if not found."""
    vault = settings.vault_path
    for path in vault.rglob(f"{note_stem}.contradictions.json"):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None
