import asyncio
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


async def fetch_repo(url: str) -> str:
    """Fetch GitHub repo content using gitingest. Returns summary + tree + code.

    Uses asyncio.to_thread so the synchronous git I/O doesn't block the event loop,
    and avoids the Windows ProactorEventLoop restriction on ingest_async's subprocess calls.
    """
    summary, tree, content = await asyncio.to_thread(
        ingest,
        source=url,
        max_file_size=50_000,       # skip files > 50 KB
        exclude_patterns=_EXCLUDE,
    )

    # Combine into structured text for the AI
    result = f"## Repository Summary\n\n{summary}\n\n## File Tree\n\n{tree}\n\n## File Contents\n\n{content}"

    # Truncate if over limit
    if len(result) > _MAX_CHARS:
        result = result[:_MAX_CHARS] + "\n\n[TRUNCATED — repository content exceeds context limit]"

    return result
