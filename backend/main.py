import asyncio
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
from .summarizer import summarize

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Summarize Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store for M0 — replaced with persistent store in M2
jobs: dict[str, dict[str, Any]] = {}

# Active WebSocket connections for log broadcast
log_connections: list[WebSocket] = []


# ── Models ────────────────────────────────────────────────────────────────────

class JobRequest(BaseModel):
    urls: list[str]
    platform: str = settings.default_platform
    model: str | None = None  # None → use platform default


class JobResponse(BaseModel):
    job_id: str
    url: str
    source_type: str
    status: str
    created_at: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def serve_frontend():
    index = FRONTEND_DIR / "index.html"
    return FileResponse(index)


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
    await broadcast_log(f"{job_id} :: RETRYING...")
    return {"job_id": job_id, "status": "queued"}


# ── WebSocket log broadcast ───────────────────────────────────────────────────

@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    log_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive ping
    except WebSocketDisconnect:
        log_connections.remove(websocket)


async def broadcast_log(message: str):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    payload = f"[{ts}] {message}"
    dead = []
    for ws in log_connections:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        log_connections.remove(ws)


# ── Job runner ────────────────────────────────────────────────────────────────

async def _run_job(job_id: str):
    job = jobs[job_id]
    try:
        await _update_job(job_id, status="fetching", progress=10)
        await broadcast_log(f"{job_id} :: FETCHING {job['source_type'].upper()} → {job['url'][:60]}")

        await _update_job(job_id, status="summarizing", progress=40)
        await broadcast_log(f"{job_id} :: SUMMARIZING via {job['platform'].upper()}:{job['model']}")

        files = await summarize(job)

        await _update_job(job_id, status="writing", progress=80, files=files)
        await broadcast_log(f"{job_id} :: WRITING {len(files)} FILE(S) TO VAULT")

        await _update_job(job_id, status="done", progress=100, files=files)
        await broadcast_log(f"{job_id} :: [SUCCESS] {len(files)} FILE(S) SAVED")

    except Exception as exc:
        await _update_job(job_id, status="failed", error=str(exc))
        await broadcast_log(f"{job_id} :: [CRITICAL_ERR] {exc}")


async def _update_job(job_id: str, **kwargs):
    jobs[job_id].update(kwargs)


# ── Static files (assets if needed later) ────────────────────────────────────

if (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
