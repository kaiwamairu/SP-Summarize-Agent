import re

_DELIMITER = re.compile(r"═══ FILE: (.+?) ═══")


def parse_output(raw: str) -> list[dict]:
    """
    Split AI output on ═══ FILE: <name> ═══ delimiters.
    Pre-cleans common model-specific wrapping before splitting.
    Returns list of {filename, content, file_type}.
    """
    cleaned = _preprocess(raw)
    parts = _DELIMITER.split(cleaned)
    # parts: [preamble, filename, content, filename, content, ...]

    files = []
    for i in range(1, len(parts) - 1, 2):
        header = parts[i].strip()
        content = parts[i + 1].strip()

        if "[ATOMIC NOTE]" in header:
            filename = header.replace("[ATOMIC NOTE]", "").strip()
            file_type = "atomic"
        elif "[MOC" in header:
            filename = header.split("[MOC")[0].strip()
            file_type = "moc"
        else:
            filename = header
            file_type = "main"

        # Sanitise filename — remove any residual brackets
        filename = filename.strip("<>[]").strip()

        if filename and content:
            files.append({"filename": filename, "content": content, "file_type": file_type})

    return files


def _preprocess(raw: str) -> str:
    """
    Strip common model-specific output wrapping:
    - Markdown code fences wrapping the entire response (some models do this)
    - Leading/trailing whitespace and blank lines
    - Thinking tags from reasoning models (DeepSeek, o3)
    """
    # Remove <think>...</think> blocks (DeepSeek R1, o3)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)

    # Remove outer ```markdown ... ``` or ``` ... ``` wrapper if it encloses the whole response
    raw = re.sub(r"^```(?:markdown)?\s*\n(.*)\n```\s*$", r"\1", raw.strip(), flags=re.DOTALL)

    return raw.strip()
