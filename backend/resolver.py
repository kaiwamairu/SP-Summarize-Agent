import re

_PATTERNS = {
    "paper": [
        r"arxiv\.org",
        r"semanticscholar\.org",
        r"openreview\.net",
        r"\.pdf$",
    ],
    "video": [
        r"youtube\.com/watch",
        r"youtu\.be/",
    ],
    "repo": [
        r"github\.com/[^/]+/[^/]+",
    ],
}


def resolve_url(url: str) -> str:
    """Return 'paper', 'video', or 'repo'. Defaults to 'paper' if unknown."""
    for source_type, patterns in _PATTERNS.items():
        if any(re.search(p, url, re.IGNORECASE) for p in patterns):
            return source_type
    return "paper"
