---
name: summarize
description: Summarize an arxiv paper / YouTube video / GitHub repo into the Obsidian vault — Claude does the summarizing (no API key), notes land in D:\NotebookLM_Claude. Trigger /summarize <url>.
trigger: /summarize
---

# /summarize

Turn a URL into structured Obsidian notes. **Claude itself** writes the summary (no OpenRouter / API key) and the `summarize-agent` MCP server handles fetching the content and writing the vault files.

## Usage

```
/summarize <url>                          # summarize one URL into the vault
/summarize <url> --skip-existing          # don't overwrite notes that already exist
/summarize <url1> <url2> ...              # summarize several sources
```

Supported sources (auto-detected): **arxiv** (`/abs/`, `/pdf/`, `/html/`), **YouTube** (`watch`, `youtu.be`), **GitHub** repos.

## Requirements

The `summarize-agent` MCP server must be registered (see `docs/MCP_SETUP.md`). In Claude Code this is wired by the project-level `.mcp.json`. The three tools it exposes:

| Tool | Purpose |
|---|---|
| `fetch_source(url)` | resolve type + fetch content + return the per-type prompt |
| `list_vault_notes()` | list existing notes (stem/folder/title/tags) to avoid dupes / find the MOC |
| `save_summary(markdown, source_type, url, on_conflict)` | parse `═══ FILE ═══` output → write vault notes |

## Workflow (follow exactly)

For each URL given:

1. **Fetch** — call `fetch_source(url)`. Keep the returned `source_type`, `content`, `prompt`, and `system_contract`.
2. **Check the vault** — call `list_vault_notes()`. Use it to:
   - detect if a note for this source already exists,
   - find the most relevant existing MOC to append to (don't invent a new MOC if a fitting one exists).
3. **Summarize** — write the summary by following `prompt` and `system_contract` **exactly**. Output **only** `═══ FILE: <filename.md> ═══` sections — a main note (always), 1–3 atomic notes (only if named reusable techniques exist), and the MOC (append if it exists, else create). Preserve the frontmatter spec from the prompt (tags, `date_created`, etc.) so the notes work with the knowledge graph + trust score.
4. **Save** — call `save_summary(markdown=<your full output>, source_type=<from step 1>, url=<the url>, on_conflict=<choice>)`.
   - `on_conflict="overwrite"` (default) — replace an existing note.
   - `on_conflict="skip"` — if `--skip-existing` was passed, or the user asked not to touch existing notes.
   - `on_conflict="rename"` — keep both; writes `<name>-2.md`.
5. **Report** — tell the user the `action` per file (created / overwritten / appended / renamed / skipped) and the vault paths.

## Notes

- The ingesters already truncate large papers/repos to a context-safe size — no need to trim manually.
- Don't call any OpenRouter/AI API — **you** are the summarizer.
- If `fetch_source` errors (bad URL, network), report it plainly and stop for that URL; continue with the others.
