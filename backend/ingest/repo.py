import httpx


async def fetch_repo(url: str) -> str:
    """Convert GitHub repo to text via gitingest.com API."""
    ingest_url = url.replace("github.com", "gitingest.com")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(ingest_url, follow_redirects=True)
        r.raise_for_status()
    # gitingest returns a text page — strip HTML tags
    import re
    text = re.sub(r"<[^>]+>", " ", r.text)
    text = re.sub(r"\s{2,}", "\n", text)
    return text.strip()
