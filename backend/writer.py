from pathlib import Path
from typing import Any

from .config import settings

_TYPE_FOLDER = {
    "main": None,        # resolved per source_type
    "atomic": "10-Atomic-Notes",
    "moc": "00-MOCs",
}


def write_files(
    parsed: list[dict],
    job: dict[str, Any],
    on_conflict: str = "overwrite",
) -> list[dict]:
    """Write parsed files to the Obsidian vault. Returns list of saved file records.

    on_conflict controls behaviour when a non-MOC note already exists:
      "overwrite" — replace the existing file (default; original behaviour)
      "skip"      — leave the existing file untouched, report action="skipped"
      "rename"    — write to "<stem>-2.md", "<stem>-3.md", … instead

    MOC files always append regardless of on_conflict (a MOC is a running index).
    """
    saved = []
    for item in parsed:
        path = _resolve_path(item, job["source_type"])
        path.parent.mkdir(parents=True, exist_ok=True)

        if item["file_type"] == "moc" and path.exists():
            _append_moc(path, item["content"])
            action = "appended"
        elif path.exists() and on_conflict == "skip":
            action = "skipped"
        elif path.exists() and on_conflict == "rename":
            path = _next_free_path(path)
            path.write_text(item["content"], encoding="utf-8")
            action = "renamed"
        else:
            existed = path.exists()
            path.write_text(item["content"], encoding="utf-8")
            action = "overwritten" if existed else "created"

        saved.append({
            "filename": path.name,
            "path": str(path),
            "file_type": item["file_type"],
            "action": action,
        })

    return saved


def _next_free_path(path: Path) -> Path:
    """Return <stem>-2.md, <stem>-3.md, … — first variant that does not exist."""
    stem, suffix, parent = path.stem, path.suffix, path.parent
    n = 2
    while True:
        candidate = parent / f"{stem}-{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def _resolve_path(item: dict, source_type: str) -> Path:
    folder_name = _TYPE_FOLDER.get(item["file_type"])
    if folder_name is None:
        folder_name = settings.vault_structure.get(
            {"paper": "papers", "video": "videos", "repo": "repos"}.get(source_type, "inbox"),
            "90-Inbox",
        )
    return settings.vault_path / folder_name / item["filename"]


def _append_moc(path: Path, new_entry: str) -> None:
    existing = path.read_text(encoding="utf-8")
    path.write_text(existing + "\n" + new_entry, encoding="utf-8")
