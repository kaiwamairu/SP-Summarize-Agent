import re
from youtube_transcript_api import YouTubeTranscriptApi


async def fetch_video(url: str) -> str:
    """Fetch YouTube transcript with timestamps."""
    video_id = _extract_id(url)
    api = YouTubeTranscriptApi()
    transcript = api.fetch(video_id)
    entries = transcript.to_raw_data()
    lines = [f"[{_fmt_ts(e['start'])}] {e['text']}" for e in entries]
    return "\n".join(lines)


def _extract_id(url: str) -> str:
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if not match:
        raise ValueError(f"Cannot extract YouTube video ID from: {url}")
    return match.group(1)


def _fmt_ts(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
