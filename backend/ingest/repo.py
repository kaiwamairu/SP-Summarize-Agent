import asyncio
import os
from gitingest import ingest  # synchronous — wrapped in to_thread to stay non-blocking

# Keep total under ~100k chars to stay within AI context limits
_MAX_CHARS = 100_000

# Per-file cap. Lower = faster ingest + skips large generated/data files.
# gitingest already shallow-clones (--depth=1); the bottleneck is reading +
# concatenating many files, so a tighter cap meaningfully cuts processing time.
_MAX_FILE_SIZE = 24_000

# Hard ceiling on the whole ingest so an MCP `fetch_source` call fails fast with a
# helpful message instead of being killed by the client's ~60s request timeout.
_INGEST_TIMEOUT_SEC = 45

# Skip binary, lock, data, notebook, and model-weight files — they bloat the
# clone/process step without adding code understanding. Data-heavy ML repos
# (datasets, instructions, checkpoints) are the main cause of timeouts.
_EXCLUDE = {
    # lock / vendor / build
    "*.lock", "package-lock.json", "yarn.lock", "poetry.lock", "pnpm-lock.yaml",
    "*.min.js", "*.min.css", "dist/", "build/", ".git/",
    "node_modules/", "__pycache__/", ".venv/", "venv/",
    # images / fonts / media
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.ico", "*.webp", "*.mp4", "*.mov",
    "*.woff", "*.woff2", "*.ttf", "*.eot",
    # notebooks (huge JSON cell outputs)
    "*.ipynb",
    # data files
    "*.csv", "*.tsv", "*.parquet", "*.arrow", "*.h5", "*.hdf5", "*.npy", "*.npz",
    "*.jsonl", "*.zip", "*.tar", "*.gz", "*.7z", "*.pdf",
    # model weights / checkpoints
    "*.pt", "*.pth", "*.bin", "*.safetensors", "*.onnx", "*.ckpt", "*.gguf", "*.pkl",
    # common data/asset directories in ML repos
    "data/", "datasets/", "dataset/", "assets/", "checkpoints/", "weights/", "outputs/",
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
        return ingest(
            source=url,
            max_file_size=_MAX_FILE_SIZE,
            exclude_patterns=_EXCLUDE,
        )
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
    LFS repos clone without downloading binary blobs. A hard timeout keeps an
    MCP call from hanging past the client's request timeout.
    """
    try:
        summary, tree, content = await asyncio.wait_for(
            asyncio.to_thread(_ingest_with_lfs_skip, url),
            timeout=_INGEST_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        raise TimeoutError(
            f"Repo ingest exceeded {_INGEST_TIMEOUT_SEC}s (repo too large or slow to clone). "
            "Try a smaller repo, or pre-fetch it via the web pipeline."
        ) from None

    # Combine into structured text for the AI
    result = f"## Repository Summary\n\n{summary}\n\n## File Tree\n\n{tree}\n\n## File Contents\n\n{content}"

    # Truncate if over limit
    if len(result) > _MAX_CHARS:
        result = result[:_MAX_CHARS] + "\n\n[TRUNCATED — repository content exceeds context limit]"

    return result
