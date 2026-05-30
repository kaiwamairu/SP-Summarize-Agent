"""
backend/graph.py

Scan the Obsidian vault and build a knowledge-graph JSON payload.

Nodes  = every .md file in the vault
Edges  = two nodes share an edge if they share ≥1 semantic tag
         (weight = number of shared tags)

The result is served by GET /api/graph in main.py.
"""

import re
from pathlib import Path
from typing import Any

import yaml

from .config import settings

# ── Folder → node_type mapping ────────────────────────────────────────────────
_FOLDER_TYPE: dict[str, str] = {
    "00-MOCs":           "moc",
    "10-Atomic-Notes":   "atomic",
    "20-Papers":         "paper",
    "30-Videos":         "video",
    "40-Repos":          "repo",
}

# Tags that add zero semantic value for clustering — skip them
_SKIP_TAGS = {"paper", "video", "repo", "atomic", "moc", "note",
              "summarized", "status", "inbox", "wip"}


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Extract YAML frontmatter between --- delimiters."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return {}


def _extract_tags(fm: dict[str, Any]) -> list[str]:
    """Return meaningful tags from frontmatter, normalised to lowercase."""
    raw = fm.get("tags", [])
    if isinstance(raw, str):
        raw = [raw]
    tags = []
    for t in (raw or []):
        t = str(t).strip().lstrip("#").lower()
        if t and t not in _SKIP_TAGS:
            tags.append(t)
    return tags


def _node_type_for(path: Path) -> str:
    """Infer node type from folder name."""
    folder = path.parent.name
    return _FOLDER_TYPE.get(folder, "note")


def _title_for(fm: dict[str, Any], path: Path) -> str:
    """Best human-readable title: frontmatter title → filename stem."""
    raw = fm.get("title", "")
    if raw:
        # Strip Thai | English pattern — keep the English part if present
        parts = str(raw).split("|")
        return parts[-1].strip() if len(parts) > 1 else str(raw).strip()
    return path.stem


def build_graph() -> dict[str, Any]:
    """
    Scan the vault and return:
      {
        "nodes": [...],
        "edges": [...],
        "tag_index": {tag: [node_id, ...]},
      }
    """
    vault = settings.vault_path
    nodes: list[dict] = []
    node_map: dict[str, dict] = {}        # node_id → node
    tag_to_nodes: dict[str, list[str]] = {}  # tag → [node_id, ...]

    for md_path in sorted(vault.rglob("*.md")):
        # Skip files outside the numbered folders (loose vault files, logs, etc.)
        relative = md_path.relative_to(vault)
        top_folder = relative.parts[0] if len(relative.parts) > 1 else ""
        if top_folder not in _FOLDER_TYPE:
            continue

        text = md_path.read_text(encoding="utf-8", errors="replace")
        fm = _parse_frontmatter(text)
        tags = _extract_tags(fm)

        node_id = md_path.stem  # filename without .md
        node_type = _node_type_for(md_path)
        title = _title_for(fm, md_path)

        # Build node preview snippet (first non-frontmatter non-empty line)
        body = re.sub(r"^---.*?---\s*\n", "", text, flags=re.DOTALL).strip()
        # Strip callout marker and take first sentence
        snippet = ""
        for line in body.splitlines():
            clean = re.sub(r"^>\s*\[!.*?\]\s*", "", line).strip()
            clean = re.sub(r"^[>#\-\*\s]+", "", clean).strip()
            if len(clean) > 20:
                snippet = clean[:120]
                break

        node = {
            "id":       node_id,
            "title":    title,
            "type":     node_type,
            "tags":     tags,
            "file":     str(md_path.relative_to(vault)).replace("\\", "/"),
            "snippet":  snippet,
            "folder":   top_folder,
        }
        nodes.append(node)
        node_map[node_id] = node

        for tag in tags:
            tag_to_nodes.setdefault(tag, []).append(node_id)

    # ── Build edges: shared tags ──────────────────────────────────────────────
    edges: list[dict] = []
    seen: set[frozenset] = set()

    for tag, nids in tag_to_nodes.items():
        for i in range(len(nids)):
            for j in range(i + 1, len(nids)):
                pair = frozenset([nids[i], nids[j]])
                if pair in seen:
                    # Find existing edge and increment weight + add tag
                    for e in edges:
                        if {e["source"], e["target"]} == pair:
                            e["weight"] += 1
                            e["shared_tags"].append(tag)
                            break
                else:
                    seen.add(pair)
                    edges.append({
                        "source":      nids[i],
                        "target":      nids[j],
                        "weight":      1,
                        "shared_tags": [tag],
                    })

    # Sort edges by weight descending for easier frontend rendering
    edges.sort(key=lambda e: e["weight"], reverse=True)

    return {
        "nodes":     nodes,
        "edges":     edges,
        "tag_index": {k: v for k, v in tag_to_nodes.items() if len(v) > 1},
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "tag_count":  len(tag_to_nodes),
        },
    }
