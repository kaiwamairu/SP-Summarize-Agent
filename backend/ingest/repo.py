import asyncio
import os
from gitingest import ingest  # synchronous — wrapped in to_thread to stay non-blocking

# Keep total under ~100k chars to stay within AI context limits
_MAX_CHARS = 100_000
# Skip binary-heavy and lock files to save tokens
_EXCLUDE = {
    "*.lock", "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg",
    "*.ico", "*.woff", "*.woff2", "*.ttf", "*.eot",
    "package-lock.json", "yarn.lock", "poetry.lock",
    "*.min.js", "*.min.css", "dist/", "build/", ".git/",
    "node_modules/", "__pycache__/",
}

# Env patch applied around every gitingest call.
# GIT_LFS_SKIP_SMUDGE=1 → git skips downloading LFS blobs during clone,
# so large repos (UI-TARS, etc.) clone successfully with code structure intact.
_GIT_ENV = {"GIT_LFS_SKIP_SMUDGE": "1"}


def _ingest_with_lfs_skip(url: str) -> tuple[str, str, str]:
    """Run ingest() with LFS blob download disabled."""
    old = {k: os.environ.get(k) for k in _GIT_ENV}
    os.environ.update(_GIT_ENV)
    try:
        return ingest(source=url, max_file_size=50_000, exclude_patterns=_EXCLUDE)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


async def fetch_repo(url: str) -> str:
    """Fetch GitHub repo content using gitingest. Returns summary + tree + code.

    Runs in a thread pool (avoids blocking the event loop and Windows
    ProactorEventLoop restriction). GIT_LFS_SKIP_SMUDGE=1 lets large
    LFS repos clone without downloading binary blobs.
    """
    summary, tree, content = await asyncio.to_thread(_ingest_with_lfs_skip, url)

    # Combine into structured text for the AI
    result = f"## Repository Summary\n\n{summary}\n\n## File Tree\n\n{tree}\n\n## File Contents\n\n{content}"

    # Truncate if over limit
    if len(result) > _MAX_CHARS:
        result = result[:_MAX_CHARS] + "\n\n[TRUNCATED — repository content exceeds context limit]"

    return result
