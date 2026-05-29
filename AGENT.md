# AGENT.md — Coding Agent Operating Protocol

> **Purpose**: Daily-work rules for the AI coding agent — session continuity, logging, and Obsidian PKM.  
> Skill review and AGENT.md self-improvement are handled by `WEEKLY_REVIEW_AGENT.md` (runs separately).  
> Read this file at the start of every session. Execute the session-start ritual before any task.

---

## 0. Session-Start Ritual (MANDATORY)

Before doing ANY work, the agent MUST:

1. **Read this file** completely.
2. **Read the project's `PROJECT_CONTEXT.md`** if it exists in the current directory.
3. **Scan `logs/chat-history/`** for the 3 most recent session logs matching this project.
4. **Report to the user**:
   - Last task completed in this project
   - Current known blockers or open TODOs
   - Skill gaps flagged in prior sessions
5. **Ask**: "Continue from last session, or start a new task?"

If no prior logs exist → state that explicitly. Do not hallucinate history.

---

## 1. Session Metadata Block

Every session log MUST begin with this YAML frontmatter:

```yaml
---
datetime: "YYYY-MM-DD HH:mm (TZ)"
model: "<model name and version>"
project: "<project name>"
project_path: "<absolute or repo-relative path>"
session_id: "<YYYY-Mon-DD-task-slug>"   # e.g. 2026-May-29-auth-refactor
user: "<name or handle>"
tags:
  - project/<project-name>
  - lang/<language>
  - domain/<domain>          # backend / ml / devops / frontend
  - task/<task-type>         # refactor / debug / design / feature
  - skill/<skill-area>
  - status/<completed|blocked|in-progress>
  - model/<model-name>
obsidian_links:
  - "[[Projects/<project>]]"
  - "[[Skills/<skill-domain>]]"
---
```

---

## 2. Task Record Format

```markdown
## Task: <short title>

### 2.1 Request
**User asked**: <exact topic or goal — no paraphrase>
**Context provided**: <files, constraints, prior decisions mentioned>
**Ambiguities clarified**: <any clarification asked before proceeding>

### 2.2 Approach
**Strategy chosen**: <why this approach, not just what>
**Alternatives considered**: <1-2 alternatives and why rejected>
**Assumptions made**: <explicit list — never hide assumptions>

### 2.3 Result
**What was created**:
| Artifact | Path | Description |
|----------|------|-------------|
| `filename.ext` | `path/to/file` | What it does |

**What was modified**:
| File | Change | Reason |
|------|--------|--------|

**Commands run**:
```bash
# exact commands only
```

**Status**: ✅ Done / ⚠️ Partial / ❌ Blocked

### 2.4 Open Items
- [ ] <unfinished or deferred work>

### 2.5 Decisions Made
- **Decision**: <what>  
  **Reason**: <why>  
  **Reversibility**: easy / hard / irreversible
```

---

## 3. Chat History Recording

### File Location
```
logs/
└── chat-history/
    └── 2026-May-29-auth-refactor.md
```

**Naming**: `YYYY-Mon-DD-task-slug.md` — no spaces, no special chars, lowercase slug.

### Format

```markdown
# Chat Log — <task-slug>
> Session: <datetime> | Model: <model> | Project: <project>

---
**[HH:mm] User**: <exact message>

**[HH:mm] Agent**: <response summary — not full verbatim>
> 📎 Artifacts: `path/to/file.ext`
> 🔧 Tools used: bash, read_file, write_file
> ⚠️ CORRECTION: <note if agent made a wrong assumption>
---
```

**Rules**:
- Summarize agent responses — do NOT paste full output verbatim
- Log every tool call and its outcome
- Log artifact paths, not artifact content
- Mark wrong assumptions with `⚠️ CORRECTION:`
- Skip filler exchanges ("ok", "thanks", "sure")

---

## 4. Obsidian Integration

### 4.1 Wikilinks Block (bottom of every session log)

```markdown
## Obsidian Links
[[Projects/<project-name>]]
[[Projects/<project-name>/decisions]]
[[Skills/<skill-area>]]
[[Concepts/<new-concept-learned>]]
[[logs/chat-history/<previous-related-session>]]
```

### 4.2 Backlink Rule
If a concept, library, or pattern appears for the **second time** across sessions → link it to the first occurrence. This is what builds the knowledge graph edges, not just tags.

---

## 5. Lightweight Self-Eval (session end — keep it fast)

> Full skill-gap analysis is done by the weekly review agent, NOT here.  
> This block exists only to feed the weekly agent good raw data.

```markdown
## Session Self-Eval

| Criterion | 1-5 | Note |
|-----------|-----|------|
| Correctness | | Did it work? |
| Efficiency | | Optimal approach? |
| Clarity | | Readable output? |
| User alignment | | Answered what was asked? |

**1 thing that went well**: <specific>
**1 thing that went wrong**: <specific>
**Skill gap flagged**: <gap> — severity: 🔴 / 🟡 / 🟢
**Agent behavior note**: <was I guessing? over-engineering? unclear?>
```

---

## 6. Project Context File (`PROJECT_CONTEXT.md`)

Created on first session, updated every session end.

```markdown
# Project: <name>
> Last updated: <datetime> by <model>

## Overview
<1-3 sentences>

## Stack
- Language / Framework / Key deps / Infrastructure

## Current Status
- Phase: planning / building / testing / deployed
- Completion: <rough %>
- Last milestone: <what was last done>

## Architecture Decisions
| # | Decision | Reason | Date |
|---|----------|--------|------|

## Open TODOs
- [ ] <task> — priority: high / med / low

## Known Blockers
- <issue + current workaround>

## Session History
| Date | Model | Task | Outcome |
|------|-------|------|---------|
```

---

## 7. Agent Rules

**Never**
- Skip the session-start ritual
- Skip the self-eval block
- Record vague outcomes ("it works") — be specific
- Hallucinate prior session context — always read the logs first
- Make architecture decisions silently

**Always**
- Write full file paths — never ambiguous
- Record the model name
- Flag when a task exceeded agent confidence level
- Write the Obsidian links block

**Prefer**
- Specific over general in all records
- Admitting uncertainty over fabricating confidence
- One clarifying question early over failing late

---

## 8. Directory Structure

```
<project-root>/
├── AGENT.md                     ← this file
├── WEEKLY_REVIEW_AGENT.md       ← weekly improvement agent (separate)
├── PROJECT_CONTEXT.md           ← per-project living state
└── logs/
    ├── chat-history/            ← daily session logs (per project)
    │   └── 2026-May-29-task.md
    └── reviews/                 ← weekly review outputs (written by review agent)
        └── 2026-W22-review.md
```

---

## 9. Limitations

- File-based memory — not a vector DB. Logs must be read explicitly.
- Self-eval quality depends on the model. Treat it as signal, not ground truth.
- Git still required for code diffs. This system records decisions and learning.
- Obsidian links work only if `logs/` is inside your vault directory.

---
*Keep this file ≤ 250 lines. If it grows: move domain rules to `docs/agent/`.*
