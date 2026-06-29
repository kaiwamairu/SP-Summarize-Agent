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

Quick sanity check the server boots over stdio (works from ANY directory thanks to the wrapper):

```bash
py -3 D:\VS_CODE_PROJECT\SP_Summarize_Project\run_mcp_server.py   # waits for JSON-RPC on stdin; Ctrl+C to exit
```

> **Why `run_mcp_server.py` and not `-m backend.mcp_server`?**
> Claude Desktop does not reliably set the working directory when it spawns the server, so
> `-m backend.mcp_server` fails with `ModuleNotFoundError: No module named 'backend'`.
> `run_mcp_server.py` puts the project root on `sys.path` itself, so it works from any cwd.

---

## A. Claude Desktop

1. Open (or create) the config file:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   = C:\Users\ryu25\AppData\Roaming\Claude\claude_desktop_config.json
   ```
   > **Microsoft Store build?** The real file Python/scripts see is the virtualized path:
   > `C:\Users\<you>\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`
   > (the `%APPDATA%` path is a redirect — Notepad/Explorer follow it, native Python does not).
2. Merge the `mcpServers` block from [`claude_desktop_config.example.json`](claude_desktop_config.example.json)
   into it (keep any servers you already have):
   ```json
   {
     "mcpServers": {
       "summarize-agent": {
         "command": "C:\\Users\\ryu25\\AppData\\Local\\Python\\pythoncore-3.14-64\\python.exe",
         "args": ["D:\\VS_CODE_PROJECT\\SP_Summarize_Project\\run_mcp_server.py"]
       }
     }
   }
   ```
3. **Restart Claude Desktop** (fully Quit from the tray — closing the window isn't enough).
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
  C:\Users\ryu25\AppData\Local\Python\pythoncore-3.14-64\python.exe \
  D:\VS_CODE_PROJECT\SP_Summarize_Project\run_mcp_server.py
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
| `ModuleNotFoundError: No module named 'backend'` | You're using `-m backend.mcp_server` — switch to `run_mcp_server.py` (Desktop ignores `cwd`) |
| `_distutils_hack` warning in logs | Harmless py3.14 noise on stderr — not an error, server still starts |
| `python` opens Microsoft Store | use the full `python.exe` path (as in the example), not bare `python` |
| FastAPI app broke after install | needs `fastapi>=0.118` on Python 3.14 — already pinned in `requirements.txt` |
| Notes overwrite each other | pass `on_conflict="skip"` or `"rename"`, or say "don't overwrite existing notes" |
