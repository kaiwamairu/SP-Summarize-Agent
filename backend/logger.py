"""
Session Logger — writes per-session job summaries to logs/chat-history/.

One Markdown file per calendar day: YYYY-Mon-DD-summarize.md
Each job run appends a single section block.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

# logs/ lives next to backend/ at the project root
_LOG_DIR = Path(__file__).parent.parent / "logs" / "chat-history"


async def session_log(
    job: dict[str, Any],
    files: list[dict],
    *,
    elapsed_sec: int = 0,
    error: str | None = None,
) -> None:
    """Async-safe: append one job result to today's session log."""
    await asyncio.to_thread(_write_entry, job, files, elapsed_sec, error)


def _log_path() -> Path:
    today = datetime.utcnow().strftime("%Y-%b-%d")   # e.g. 2025-May-30
    return _LOG_DIR / f"{today}-summarize.md"


def _write_entry(
    job: dict[str, Any],
    files: list[dict],
    elapsed_sec: int,
    error: str | None,
) -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = _log_path()

    # Write file header if brand new
    if not path.exists():
        path.write_text(
            f"# Summarize Agent — Session Log\n"
            f"date: {datetime.utcnow().strftime('%Y-%m-%d')}\n\n"
            "---\n\n",
            encoding="utf-8",
        )

    ts = datetime.utcnow().strftime("%H:%M:%S UTC")
    if error:
        status_line = f"❌ FAILED — {error}"
    else:
        status_line = f"✅ SUCCESS ({elapsed_sec}s)"

    lines: list[str] = [
        f"## [{ts}] {job['job_id']}",
        "",
        f"- **URL**: {job['url']}",
        f"- **Type**: `{job['source_type']}`",
        f"- **Platform**: `{job['platform']}` / `{job['model']}`",
        f"- **Status**: {status_line}",
    ]

    if files:
        lines.append("- **Files written**:")
        for f in files:
            action = f.get("action", "created")
            lines.append(f"  - `{f['filename']}` [{f['file_type']}] ({action})")

    lines += ["", "---", ""]

    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
