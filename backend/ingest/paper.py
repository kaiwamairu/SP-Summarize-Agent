import re
import httpx

# Max chars to send to AI — keeps within ~100k token context
_MAX_CHARS = 120_000


async def fetch_paper(url: str) -> str:
    """Fetch arxiv paper. Tries HTML version first, falls back to abs page."""
    html_url = _to_html_url(url)
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        r = await client.get(html_url)
        if r.status_code == 200 and "html" in r.headers.get("content-type", ""):
            return _extract_arxiv_html(r.text)
        # Fallback: abstract page
        r2 = await client.get(url)
        r2.raise_for_status()
        return _extract_arxiv_html(r2.text)


def _to_html_url(url: str) -> str:
    """Convert any arxiv URL form to the HTML viewer URL."""
    # /abs/2404.01234  → /html/2404.01234
    url = re.sub(r"(arxiv\.org)/abs/", r"\1/html/", url)
    # /pdf/2404.01234v1.pdf or /pdf/2404.01234 → /html/2404.01234
    url = re.sub(r"(arxiv\.org)/pdf/(\d+\.\d+)(?:v\d+)?(?:\.pdf)?", r"\1/html/\2", url)
    return url


def _extract_arxiv_html(html: str) -> str:
    """Extract meaningful text from arxiv HTML, preserving structure."""
    # Remove script, style, nav, footer noise
    html = re.sub(r"<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)

    # Mark section boundaries before stripping tags
    html = re.sub(r"<h([1-4])[^>]*>(.*?)</h\1>", r"\n\n## \2\n\n", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<p[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<li[^>]*>", "\n- ", html, flags=re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", html)

    # Decode common HTML entities
    entities = {"&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"',
                "&#39;": "'", "&nbsp;": " ", "&#x27;": "'"}
    for ent, char in entities.items():
        text = text.replace(ent, char)

    # Collapse whitespace but preserve paragraph breaks
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()

    # Truncate to token-safe size
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS] + "\n\n[TRUNCATED — paper continues beyond context limit]"

    return text
