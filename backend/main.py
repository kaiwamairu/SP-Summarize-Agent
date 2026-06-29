import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .resolver import resolve_url
from .summarizer import fetch_content, call_ai_raw
from .parser import parse_output
from .writer import write_files
from .logger import session_log
from .graph import build_graph
from .retagger import retag_vault
from .scorer import score_vault
from .extractor import extract_vault, load_claims
from .contradictor import detect_vault, load_contradictions, scan_all_contradictions
from .auditor import run_full_audit

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Summarize Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store
jobs: dict[str, dict[str, Any]] = {}

# Active WebSocket connections
log_connections: list[WebSocket] = []

# M4: max 3 concurrent AI calls
_ai_semaphore = asyncio.Semaphore(3)


# ── Models ────────────────────────────────────────────────────────────────────

class JobRequest(BaseModel):
    urls: list[str]
    platform: str = settings.default_platform
    model: str | None = None  # None → use platform default


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/graph.html")
async def serve_graph():
    return FileResponse(FRONTEND_DIR / "graph.html")


@app.get("/api/settings")
async def get_settings():
    return {
        "vault_path": str(settings.vault_path),
        "default_platform": settings.default_platform,
        "platforms": {
            name: {
                "model": cfg["model"],
                "models_available": cfg["models_available"],
            }
            for name, cfg in settings.platforms.items()
        },
        "synthesis_flags": settings.synthesis_flags,
    }


@app.post("/api/jobs")
async def create_jobs(req: JobRequest):
    created = []
    for url in req.urls:
        url = url.strip()
        if not url:
            continue
        source_type = resolve_url(url)
        job_id = f"JOB_{uuid.uuid4().hex[:6].upper()}"
        job = {
            "job_id": job_id,
            "url": url,
            "source_type": source_type,
            "platform": req.platform,
            "model": req.model or settings.platforms[req.platform]["model"],
            "status": "queued",
            "progress": 0,
            "log": [],
            "files": [],
            "error": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        jobs[job_id] = job
        created.append(job)
        asyncio.create_task(_run_job(job_id))

    return JSONResponse(content={"jobs": created})


@app.get("/api/jobs")
async def list_jobs():
    return {"jobs": list(jobs.values())}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    return job


@app.get("/api/vault/note")
async def get_vault_note(note_file: str):
    """Return full markdown content of a vault note + Obsidian deep-link URL.

    Query param: note_file = path relative to vault root, e.g. '20-Papers/2023-gpt4.md'
    """
    try:
        path = (settings.vault_path / note_file).resolve()
        vault_resolved = settings.vault_path.resolve()
        if not str(path).startswith(str(vault_resolved)):
            return JSONResponse(status_code=403, content={"error": "Access denied"})
        if not path.exists() or path.suffix != ".md":
            return JSONResponse(status_code=404, content={"error": "Note not found"})
        content = path.read_text(encoding="utf-8", errors="replace")
        vault_name = settings.vault_path.name
        obs_path = note_file.replace("\\", "/")
        if obs_path.endswith(".md"):
            obs_path = obs_path[:-3]
        obsidian_url = f"obsidian://open?vault={vault_name}&file={obs_path}"
        return {"file": note_file, "content": content, "obsidian_url": obsidian_url}
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/graph")
async def get_graph():
    """Return vault knowledge graph (nodes + tag-based edges)."""
    try:
        data = await asyncio.to_thread(build_graph)
        return JSONResponse(content=data)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


class RetagRequest(BaseModel):
    dry_run: bool = False   # True → return plan without writing files
    platform: str = settings.default_platform
    model: str | None = None


@app.post("/api/vault/retag")
async def vault_retag(req: RetagRequest):
    """
    Scan existing vault .md files and enrich their semantic tags using AI.
    Posts progress via WebSocket log messages.
    """
    model = req.model or settings.platforms[req.platform]["model"]
    asyncio.create_task(
        _run_retag(req.platform, model, dry_run=req.dry_run)
    )
    return {"status": "started", "platform": req.platform, "model": model, "dry_run": req.dry_run}


async def _run_retag(platform: str, model: str, *, dry_run: bool):
    await _emit_log(f"RETAG :: Starting vault retag (platform={platform} model={model} dry_run={dry_run})")
    try:
        results = await retag_vault(platform, model, dry_run=dry_run, emit_log=_emit_log)
        await _emit_log(f"RETAG :: Done — {results['updated']} updated, {results['skipped']} skipped, {results['errors']} errors")
        await _broadcast({"type": "retag_done", "results": results})
    except Exception as exc:
        await _emit_log(f"RETAG :: [ERROR] {type(exc).__name__}: {exc}")


# ── Vault Audit (Trust Score) ─────────────────────────────────────────────────

class AuditRequest(BaseModel):
    dry_run: bool = False


@app.post("/api/vault/audit")
async def vault_audit(req: AuditRequest):
    """Score trust for all vault notes. Rule-based only — no AI cost."""
    asyncio.create_task(_run_audit(dry_run=req.dry_run))
    return {"status": "started", "dry_run": req.dry_run}


async def _run_audit(*, dry_run: bool):
    await _emit_log(f"AUDIT :: Starting trust score run (dry_run={dry_run})")
    try:
        results = await score_vault(dry_run=dry_run, emit_log=_emit_log)
        await _emit_log(
            f"AUDIT :: Done — {results['updated']} scored, "
            f"{results['skipped']} skipped, {results['errors']} errors"
        )
        await _broadcast({"type": "audit_done", "results": results})
    except Exception as exc:
        await _emit_log(f"AUDIT :: [ERROR] {type(exc).__name__}: {exc}")


# ── Claim Extraction (M6b) ────────────────────────────────────────────────────

class ExtractRequest(BaseModel):
    dry_run:  bool       = False
    platform: str        = settings.default_platform
    model:    str | None = None


@app.post("/api/vault/extract")
async def vault_extract(req: ExtractRequest):
    """
    Run AI claim extraction over all vault notes (incremental).
    Each note gets a sidecar .claims.json. Token cost: one small AI call per dirty note.
    """
    model = req.model or settings.platforms[req.platform]["model"]
    asyncio.create_task(_run_extract(req.platform, model, dry_run=req.dry_run))
    return {"status": "started", "platform": req.platform, "model": model, "dry_run": req.dry_run}


async def _run_extract(platform: str, model: str, *, dry_run: bool):
    await _emit_log(
        f"EXTRACT :: Starting claim extraction "
        f"(platform={platform} model={model} dry_run={dry_run})"
    )
    try:
        results = await extract_vault(
            platform, model, dry_run=dry_run, emit_log=_emit_log
        )
        await _emit_log(
            f"EXTRACT :: Done -- {results['extracted']} extracted, "
            f"{results['skipped']} skipped, {results['errors']} errors"
        )
        await _broadcast({"type": "extract_done", "results": results})
    except Exception as exc:
        await _emit_log(f"EXTRACT :: [ERROR] {type(exc).__name__}: {exc}")


@app.get("/api/vault/claims/{note_stem}")
async def get_note_claims(note_stem: str):
    """Return the .claims.json sidecar for a specific note by stem name."""
    data = load_claims(note_stem)
    if data is None:
        return JSONResponse(status_code=404, content={"error": "Claims not found — run /api/vault/extract first"})
    return JSONResponse(content=data)


# ── Contradiction Detection (M6c) ─────────────────────────────────────────────

class ContradictRequest(BaseModel):
    dry_run:  bool       = False
    platform: str        = settings.default_platform
    model:    str | None = None


@app.post("/api/vault/contradict")
async def vault_contradict(req: ContradictRequest):
    """
    Compare claims across same-tag note groups and detect contradictions.
    Capped at 40 pairs per run. Token cost: one AI call per dirty pair.
    """
    model = req.model or settings.platforms[req.platform]["model"]
    asyncio.create_task(_run_contradict(req.platform, model, dry_run=req.dry_run))
    return {"status": "started", "platform": req.platform, "model": model, "dry_run": req.dry_run}


async def _run_contradict(platform: str, model: str, *, dry_run: bool):
    await _emit_log(
        f"CONTRADICT :: Starting contradiction detection "
        f"(platform={platform} model={model} dry_run={dry_run})"
    )
    try:
        results = await detect_vault(
            platform, model, dry_run=dry_run, emit_log=_emit_log
        )
        await _emit_log(
            f"CONTRADICT :: Done -- {results['checked']} checked, "
            f"{results['found']} contradiction(s), {results['errors']} errors"
        )
        await _broadcast({"type": "contradict_done", "results": results})
    except Exception as exc:
        await _emit_log(f"CONTRADICT :: [ERROR] {type(exc).__name__}: {exc}")


@app.get("/api/vault/contradictions")
async def get_all_contradictions():
    """Scan all contradiction sidecars in vault and return a deduplicated edge list for the graph overlay."""
    try:
        data = await asyncio.to_thread(scan_all_contradictions)
        return JSONResponse(content=data)
    except Exception as exc:
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/api/vault/contradictions/{note_stem}")
async def get_note_contradictions(note_stem: str):
    """Return contradiction sidecar for a specific note."""
    data = load_contradictions(note_stem)
    if data is None:
        return JSONResponse(
            status_code=404,
            content={"error": "No contradiction data — run /api/vault/contradict first"},
        )
    return JSONResponse(content=data)


@app.get("/api/vault/trust")
async def get_trust_scores():
    """
    Return trust scores for every vault note that has been scored.
    Fast — just reads frontmatter, no AI.
    """
    import re as _re
    import yaml as _yaml

    vault = settings.vault_path
    folder_map = {"00-MOCs", "10-Atomic-Notes", "20-Papers", "30-Videos", "40-Repos"}
    scores: dict[str, dict] = {}

    for path in sorted(vault.rglob("*.md")):
        if path.parent.name not in folder_map:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            m = _re.match(r"^---\s*\n(.*?)\n---", text, _re.DOTALL)
            if not m:
                continue
            fm = _yaml.safe_load(m.group(1)) or {}
            trust = fm.get("trust")
            if trust:
                scores[path.stem] = trust
        except Exception:
            continue

    return JSONResponse(content={"scores": scores, "count": len(scores)})


# ── Full Audit Pipeline (M6d) ─────────────────────────────────────────────────

class FullAuditRequest(BaseModel):
    run_trust:      bool       = True
    run_extract:    bool       = True
    run_contradict: bool       = True
    dry_run:        bool       = False
    platform:       str        = settings.default_platform
    model:          str | None = None


@app.post("/api/vault/full-audit")
async def vault_full_audit(req: FullAuditRequest):
    """
    Run the complete M6 audit pipeline:
      1. Trust Score (rule-based)
      2. Claim Extraction (AI per dirty note)
      3. Contradiction Detection (AI per dirty pair)
    Each step is individually togglable via flags.
    """
    model = req.model or settings.platforms[req.platform]["model"]
    asyncio.create_task(
        _run_full_audit(
            req.platform, model,
            run_trust=req.run_trust,
            run_extract=req.run_extract,
            run_contradict=req.run_contradict,
            dry_run=req.dry_run,
        )
    )
    return {
        "status": "started",
        "platform": req.platform,
        "model": model,
        "steps": {
            "trust":      req.run_trust,
            "extract":    req.run_extract,
            "contradict": req.run_contradict,
        },
        "dry_run": req.dry_run,
    }


async def _run_full_audit(
    platform: str,
    model: str,
    *,
    run_trust: bool,
    run_extract: bool,
    run_contradict: bool,
    dry_run: bool,
):
    await _emit_log(f"AUDIT_FULL :: Pipeline starting (platform={platform} model={model})")
    try:
        summary = await run_full_audit(
            platform, model,
            run_trust=run_trust,
            run_extract=run_extract,
            run_contradict=run_contradict,
            dry_run=dry_run,
            emit_log=_emit_log,
        )
        await _broadcast({"type": "full_audit_done", "summary": summary})
    except Exception as exc:
        await _emit_log(f"AUDIT_FULL :: [CRITICAL] {type(exc).__name__}: {exc}")


@app.post("/api/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "Job not found"})
    if job["status"] not in ("failed", "done"):
        return JSONResponse(status_code=400, content={"error": "Only failed or done jobs can be retried"})
    job.update(status="queued", progress=0, files=[], error=None)
    asyncio.create_task(_run_job(job_id))
    await _emit_log(f"{job_id} :: RETRYING...")
    return {"job_id": job_id, "status": "queued"}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    log_connections.append(websocket)
    # Push current state snapshot on connect so late-joining clients sync up
    for job in jobs.values():
        try:
            await websocket.send_text(json.dumps({"type": "job_update", "job": job}))
        except Exception:
            pass
    try:
        while True:
            await websocket.receive_text()  # keep-alive pings from client
    except WebSocketDisconnect:
        if websocket in log_connections:
            log_connections.remove(websocket)


async def _broadcast(payload: dict):
    """Send a typed JSON message to all connected clients."""
    text = json.dumps(payload)
    dead: list[WebSocket] = []
    for ws in log_connections:
        try:
            await ws.send_text(text)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in log_connections:
            log_connections.remove(ws)


async def _emit_log(message: str):
    """Broadcast a timestamped log line."""
    ts = datetime.utcnow().strftime("%H:%M:%S")
    await _broadcast({"type": "log", "message": f"[{ts}] {message}"})


async def _emit_job(job_id: str):
    """Broadcast the full current state of one job."""
    await _broadcast({"type": "job_update", "job": jobs[job_id]})


async def _update_and_emit(job_id: str, **kwargs):
    """Patch job fields and immediately push the update via WS."""
    jobs[job_id].update(kwargs)
    await _emit_job(job_id)


# ── Job runner ────────────────────────────────────────────────────────────────
#
# Progress map:
#   0   queued
#  10   fetching — ingestion started
#  30   fetching — content retrieved
#  45   summarizing — AI call dispatched
#  75   parsing — AI responded, splitting output
#  85   writing — vault I/O
# 100   done

async def _run_job(job_id: str):
    job = jobs[job_id]
    t_start = datetime.utcnow()

    try:
        # ── 1. Fetch content ──────────────────────────────────────────────────
        await _update_and_emit(job_id, status="fetching", progress=10)
        await _emit_log(
            f"{job_id} :: FETCHING {job['source_type'].upper()} → {job['url'][:60]}"
        )

        content = await fetch_content(job)

        await _update_and_emit(job_id, status="fetching", progress=30)
        await _emit_log(f"{job_id} :: FETCHED {len(content):,} chars")

        # ── 2. AI call — semaphore limits to 3 concurrent ────────────────────
        async with _ai_semaphore:
            await _update_and_emit(job_id, status="summarizing", progress=45)
            await _emit_log(
                f"{job_id} :: CALLING AI → {job['platform'].upper()} / {job['model']}"
            )

            raw = await call_ai_raw(
                job["platform"], job["model"], job["source_type"], content
            )

        # ── 3. Parse AI output ────────────────────────────────────────────────
        await _update_and_emit(job_id, status="parsing", progress=75)
        await _emit_log(f"{job_id} :: AI DONE — PARSING OUTPUT")

        parsed = parse_output(raw)

        # ── 4. Write to vault ─────────────────────────────────────────────────
        await _update_and_emit(job_id, status="writing", progress=85)
        await _emit_log(f"{job_id} :: WRITING {len(parsed)} FILE(S) TO VAULT")

        saved = write_files(parsed, job)

        # ── 5. Done ───────────────────────────────────────────────────────────
        await _update_and_emit(job_id, status="done", progress=100, files=saved)
        await _emit_log(f"{job_id} :: [SUCCESS] {len(saved)} FILE(S) SAVED")

        elapsed = int((datetime.utcnow() - t_start).total_seconds())
        await session_log(job, saved, elapsed_sec=elapsed)

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        await _update_and_emit(job_id, status="failed", error=error_msg)
        await _emit_log(f"{job_id} :: [CRITICAL_ERR] {error_msg}")
        await session_log(job, [], error=error_msg)
    except BaseException as exc:
        # Catch CancelledError and other non-Exception base exceptions
        error_msg = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
        jobs[job_id].update(status="failed", error=error_msg)
        raise  # re-raise so asyncio task machinery handles it properly


# ── Static files ──────────────────────────────────────────────────────────────

if (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
