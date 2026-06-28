# Summarize Agent — MCP Setup

Turn the Summarize Agent into a tool you can call from **Claude Desktop** and **Claude Code**.
Claude itself writes the summary — **no OpenRouter / API key needed**. The MCP server only
fetches the source and writes notes into your Obsidian vault (`D:\NotebookLM_Claude`).

## What you get

Three tools + one slash command:

| Name | Type | What it does |
|---|---|---|
| `fetch_source(url)` | tool | resolve type (paper/video/repo) + fetch content + return the prompt |
| `save_summary(markdown, source_type, url, on_conflict)` | tool | parse `═══ FILE ═══` → write vault notes |
| `list_vault_notes()` | tool | list existing notes so Claude avoids dupes / finds the MOC |
| `/summarize <url>` | prompt | one-click workflow that chains the three tools |

## Prerequisites

```bash
# from the project root
py -3 -m pip install -r requirements.txt   # includes mcp>=1.28
```

Quick sanity check the server boots over stdio:

```bash
py -3 -m backend.mcp_server   # should sit waiting for JSON-RPC on stdin; Ctrl+C to exit
```

---

## A. Claude Desktop

1. Open (or create) the config file:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   = C:\Users\ryu25\AppData\Roaming\Claude\claude_desktop_config.json
   ```
2. Merge the `mcpServers` block from [`claude_desktop_config.example.json`](claude_desktop_config.example.json)
   into it (keep any servers you already have):
   ```json
   {
     "mcpServers": {
       "summarize-agent": {
         "command": "C:\\Users\\ryu25\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe",
         "args": ["-m", "backend.mcp_server"],
         "cwd": "D:\\VS_CODE_PROJECT\\SP_Summarize_Project"
       }
     }
   }
   ```
3. **Restart Claude Desktop.**
4. You should see `summarize-agent` under the tools (🔌) menu, and `/summarize` in the slash-command list.

Use it:
```
/summarize https://arxiv.org/abs/2310.06825
```
or just type naturally: *"summarize https://arxiv.org/abs/2310.06825 into my vault."*

---

## B. Claude Code

The project ships a [`.mcp.json`](../.mcp.json) — Claude Code picks it up automatically when you
open this folder. Approve the server when prompted, then:

```
/summarize https://github.com/langchain-ai/langgraph
```

The `/summarize` skill lives at `.claude/skills/summarize/SKILL.md`.

To make it available **outside** this project too, register the server at user scope:
```bash
claude mcp add summarize-agent -s user -- \
  C:\Users\ryu25\AppData\Local\Python\pythoncore-3.14-64\python.exe -m backend.mcp_server
```
(then move the skill to `~/.claude/skills/` if you want `/summarize` everywhere).

---

## How it flows

```
You:  /summarize <url>
  │
  ├─ fetch_source(url)      → {source_type, content, prompt, system_contract}
  ├─ list_vault_notes()     → existing notes (dedupe / find MOC)
  ├─ (Claude summarizes — follows the ═══ FILE ═══ contract)
  └─ save_summary(md, …)    → notes written to D:\NotebookLM_Claude
                              main note + atomic notes + MOC (appended)
```

Notes land with full frontmatter (`tags`, `date_created`, …) so they immediately work with the
knowledge graph (`/graph.html`) and the M6 trust-score / audit pipeline.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Server not listed in Desktop | Check the JSON is valid (no trailing comma), restart Desktop, confirm the `cwd` path exists |
| `ModuleNotFoundError: backend` | `cwd` must be the project root; the example config sets it |
| `python` opens Microsoft Store | use the full `python.exe` path (as in the example), not bare `python` |
| FastAPI app broke after install | needs `fastapi>=0.118` on Python 3.14 — already pinned in `requirements.txt` |
| Notes overwrite each other | pass `on_conflict="skip"` or `"rename"`, or say "don't overwrite existing notes" |
