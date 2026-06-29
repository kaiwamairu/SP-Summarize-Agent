"""
backend/auditor.py

Auditor Orchestrator — M6d

Runs the full M6 pipeline in sequence:
  1. Trust Score   (scorer.py   — rule-based, zero AI cost)
  2. Claim Extract (extractor.py — AI per dirty note)
  3. Contradiction (contradictor.py — AI per dirty pair)

Each step is optional and controlled by AuditPipelineRequest flags.
Progress is broadcast via WebSocket log messages.

Usage:
  POST /api/vault/full-audit
  { "run_trust": true, "run_extract": true, "run_contradict": true,
    "platform": "openrouter", "model": null, "dry_run": false }
"""

from __future__ import annotations

from typing import Any, Callable, Coroutine

from .scorer import score_vault
from .extractor import extract_vault
from .contradictor import detect_vault

EmitFn = Callable[[str], Coroutine[Any, Any, None]]


async def run_full_audit(
    platform: str,
    model: str,
    *,
    run_trust: bool = True,
    run_extract: bool = True,
    run_contradict: bool = True,
    dry_run: bool = False,
    emit_log: EmitFn,
) -> dict[str, Any]:
    """
    Orchestrate the full audit pipeline.
    Returns a summary dict with results from each enabled step.
    """
    summary: dict[str, Any] = {}

    # ── Step 1: Trust Score ────────────────────────────────────────────────────
    if run_trust:
        await emit_log("AUDIT_FULL :: [1/3] Trust Score (rule-based)")
        try:
            trust_results = await score_vault(dry_run=dry_run, emit_log=emit_log)
            summary["trust"] = trust_results
            await emit_log(
                f"AUDIT_FULL :: Trust done -- "
                f"{trust_results['updated']} updated, {trust_results['skipped']} skipped"
            )
        except Exception as exc:
            await emit_log(f"AUDIT_FULL :: Trust [ERROR] {type(exc).__name__}: {exc}")
            summary["trust"] = {"error": str(exc)}
    else:
        await emit_log("AUDIT_FULL :: [1/3] Trust Score -- SKIPPED")

    # ── Step 2: Claim Extraction ───────────────────────────────────────────────
    if run_extract:
        await emit_log(f"AUDIT_FULL :: [2/3] Claim Extraction ({platform}/{model})")
        try:
            extract_results = await extract_vault(
                platform, model, dry_run=dry_run, emit_log=emit_log
            )
            summary["extract"] = extract_results
            await emit_log(
                f"AUDIT_FULL :: Extract done -- "
                f"{extract_results['extracted']} extracted, {extract_results['skipped']} skipped"
            )
        except Exception as exc:
            await emit_log(f"AUDIT_FULL :: Extract [ERROR] {type(exc).__name__}: {exc}")
            summary["extract"] = {"error": str(exc)}
    else:
        await emit_log("AUDIT_FULL :: [2/3] Claim Extraction -- SKIPPED")

    # ── Step 3: Contradiction Detection ───────────────────────────────────────
    if run_contradict:
        await emit_log(f"AUDIT_FULL :: [3/3] Contradiction Detection ({platform}/{model})")
        try:
            contradict_results = await detect_vault(
                platform, model, dry_run=dry_run, emit_log=emit_log
            )
            summary["contradict"] = contradict_results
            await emit_log(
                f"AUDIT_FULL :: Contradict done -- "
                f"{contradict_results['checked']} checked, "
                f"{contradict_results['found']} contradiction(s)"
            )
        except Exception as exc:
            await emit_log(f"AUDIT_FULL :: Contradict [ERROR] {type(exc).__name__}: {exc}")
            summary["contradict"] = {"error": str(exc)}
    else:
        await emit_log("AUDIT_FULL :: [3/3] Contradiction Detection -- SKIPPED")

    await emit_log("AUDIT_FULL :: Pipeline complete.")
    return summary
