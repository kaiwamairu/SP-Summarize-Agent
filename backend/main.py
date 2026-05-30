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
