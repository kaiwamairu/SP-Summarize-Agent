# Project: [Summarize-Agent]
<!-- 
  HOW TO USE THIS FILE
  ─────────────────────
  - Agent reads this at session START (before any task)
  - Agent updates this at session END (after self-eval is written)
  - You can edit manually anytime — this is YOUR document, not the agent's
  - Keep it under 150 lines total. If it grows: you're logging, not summarizing.
  - Rule: every section should be readable in under 30 seconds
-->

> **Last updated**: YYYY-MM-DD HH:mm | by: [model name]  
> **Obsidian**: [[Projects/your-project-name]]

---

## 1. What Is This Project?

<!--
  WRITE: 2-4 sentences max. Answer 3 questions:
  1. What problem does it solve? (not what it does — why it exists)
  2. Who uses it? (yourself, a client, a team, the public?)
  3. What does "done" look like at the highest level?

  BAD: "A web app that manages tasks."
  GOOD: "A personal task router that ingests emails + Telegram messages and
         surfaces the 3 highest-priority items each morning. Done = I stop
         checking 4 different apps every day."

  The agent uses this to understand intent, not just function.
  When the agent knows WHY, it makes better decisions without asking you.
-->

**Problem**: AI news, technique, paper, interest project update so fast and i have no time to read and test everythings. and i want to collecting knowledge from that sources. Input are papers, video, repo in Github.

**Users**: Me

**Definition of done**: Create automate workflow to collect all of knowledges in obsidian, transform those source to podcast, short-summarize or testing.

---

## 2. Tech Stack

<!--
  WRITE: Be precise. Don't write "Python backend" — write the version.
  The agent needs exact versions to avoid suggesting incompatible libraries.

  Include:
  - Language + version
  - Framework + version
  - Key libraries (only the ones that affect architecture decisions)
  - Infrastructure (local / Docker / cloud provider / serverless)
  - Database + ORM if any
  - Test framework
-->

| Layer | Choice | Version | Notes |
|-------|--------|---------|-------|
| Language | | | |
| Framework | | | |
| Database | | | |
| Infra | | | |
| Testing | | | |
| Key libs | | | |

---

## 3. Repository / Path Map

<!--
  WRITE: Where is the critical code? Agent wastes tokens exploring structure
  if you don't tell it. Map the things that matter, not everything.

  Example:
  - Entry point: `src/main.py`
  - API routes: `src/api/routes/`
  - DB models: `src/models/`
  - Config: `.env` + `config/settings.py`
  - Tests: `tests/` (pytest)
  - Logs: `logs/` (this system)

  Skip auto-generated folders (node_modules, __pycache__, .venv)
-->

- Entry point: 
- Core logic: 
- Config: 
- Tests: 
- Logs: `logs/chat-history/` + `logs/reviews/`

---

## 4. Current Status

<!--
  WRITE: Be honest. This is the most important section for session continuity.
  The agent reads this first to understand where work left off.

  Phase options: planning → building → testing → stabilizing → deployed → paused → abandoned
  
  Completion %: rough estimate is fine. "~40%" is better than leaving it blank.
  It helps the agent calibrate how much scaffolding exists vs how much to build fresh.

  Last session summary: 1-2 sentences. What was actually done last time?
  This is NOT a changelog — it's the agent's "previously on..." briefing.
-->

- **Phase**: [planning / building / testing / stabilizing / deployed / paused]
- **Completion**: ~__%
- **Last session** (YYYY-MM-DD): 

---

## 5. Milestone Map

<!--
  WRITE: This is your progression tracker — the core of this document.
  
  HOW TO THINK ABOUT MILESTONES:
  A milestone is a state change in the project, not a task.
  - BAD milestone: "Write the auth module" (that's a task)
  - GOOD milestone: "User can log in and log out" (that's a state the project enters)

  Why this distinction matters:
  Tasks get done or abandoned. States are verifiable. 
  The agent (and you) can check "is this milestone reached?" with a yes/no.

  SUGGESTED STRUCTURE for most projects:
  M0 — Foundation: can I run it locally? does the skeleton exist?
  M1 — Core loop: does the primary user action work end-to-end (even badly)?
  M2 — Robustness: does it handle errors, edge cases, and bad input?
  M3 — Quality: is it tested, documented, and not embarrassing to show?
  M4 — Deployed / Delivered: is it running somewhere real?
  
  Status options: ⬜ not started | 🔄 in progress | ✅ done | 🚫 blocked | ⏭️ skipped
-->

| # | Milestone | Status | Completed |
|---|-----------|--------|-----------|
| M0 | Environment runs locally, skeleton in place | ⬜ | |
| M1 | Core user flow works end-to-end (happy path) | ⬜ | |
| M2 | Error handling, edge cases, validation done | ⬜ | |
| M3 | Tests written, code cleaned, README done | ⬜ | |
| M4 | Deployed / delivered to intended audience | ⬜ | |

<!-- Add project-specific milestones between M1 and M4 as needed -->

**Current milestone in progress**: M__

---

## 6. Open TODOs

<!--
  WRITE: Tasks that are known but not yet assigned to a session.
  NOT a full backlog. Max 10 items. If you have more, put them in a separate backlog file.

  Priority: 🔴 blocking progress | 🟡 important but not blocking | 🟢 nice-to-have

  The agent scans this to suggest what to work on when you start a new session
  without a specific task in mind.
-->

- [ ] 🔴 
- [ ] 🟡 
- [ ] 🟢 

---

## 7. Known Blockers

<!--
  WRITE: What is actively stopping progress right now?
  Include: what the blocker is, when it was identified, and current workaround (if any).
  
  If no blockers: write "None currently." Don't leave blank — blank looks like "forgotten".

  The agent uses this to avoid wasting time on blocked paths.
-->

- None currently.

---

## 8. Architecture Decisions (ADR-lite)

<!--
  WRITE: Significant choices that affect the whole project and are hard to reverse.
  
  WHAT COUNTS as an architecture decision:
  ✅ "Use PostgreSQL instead of SQLite" — affects deployment, queries, migrations
  ✅ "No authentication for v1" — affects security posture and future work
  ✅ "All API responses return JSON, never HTML" — affects every endpoint
  
  WHAT DOES NOT count:
  ❌ "Use f-strings for formatting" — that's a style preference
  ❌ "Write tests for the login module" — that's a task

  Status options: active | superseded by ADR-X | deprecated

  WHY THIS MATTERS FOR THE AGENT:
  Without this, the agent will propose solutions that conflict with decisions you already made.
  Example: if you decided "no ORM, raw SQL only," the agent needs to know — otherwise
  it will suggest SQLAlchemy in every session that touches the database.
-->

| # | Decision | Reason | Status | Date |
|---|----------|--------|--------|------|
| 1 | | | active | |

---

## 9. Session History

<!--
  WRITE: The agent appends one row here at the end of each session.
  You should NOT edit this section manually — let the agent maintain it.
  
  This is the progression log. Over time it shows:
  - How fast the project is moving
  - Which parts of the project get revisited repeatedly (may signal design problems)
  - Which models performed well on which types of tasks

  Keep the "Task" column as a slug, not a sentence. "auth-refactor" not "I refactored the auth module."
  Keep "Outcome" as one of: ✅ done | ⚠️ partial | ❌ blocked
-->

| Date | Model | Milestone | Task | Outcome |
|------|-------|-----------|------|---------|
| | | | | |

---

## 10. Skills Being Built in This Project

<!--
  WRITE: What technical skills are you intentionally developing through this project?
  The agent uses this to calibrate HOW it helps — more explanation vs less, 
  more scaffold vs letting you figure it out.

  Current level options: learning | familiar | comfortable | proficient
  
  This section + the weekly review agent = your personal curriculum.
  When the weekly agent reads this, it can see whether the skills you're
  "learning" are actually appearing in the session logs with improvement over time.
  If they're not, that's a gap worth flagging.
-->

| Skill | Level now | Target | Notes |
|-------|-----------|--------|-------|
| | learning | comfortable | |

---

<!-- 
  AGENT UPDATE INSTRUCTIONS (read at session end):
  
  After each session, update ONLY these sections:
  - Section 4 "Current Status": update phase, %, and last session line
  - Section 5 "Milestone Map": change status of any milestone that moved
  - Section 6 "Open TODOs": check off completed items, add newly discovered ones
  - Section 7 "Known Blockers": add or remove blockers
  - Section 9 "Session History": append one row
  
  Do NOT rewrite the whole file. Surgical edits only.
  Do NOT change Section 1, 2, 3, or 8 unless explicitly asked by the user.
  Those sections represent stable decisions, not session state.
-->
