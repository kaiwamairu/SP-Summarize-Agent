import re

_DELIMITER = re.compile(r"═══ FILE: (.+?) ═══")


def parse_output(raw: str) -> list[dict]:
    """
    Split Claude/AI output on ═══ FILE: <name> ═══ delimiters.
    Returns list of {filename, content, file_type}.
    """
    parts = _DELIMITER.split(raw)
    # parts alternates: [preamble, filename, content, filename, content, ...]
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

        files.append({"filename": filename, "content": content, "file_type": file_type})

    return files
