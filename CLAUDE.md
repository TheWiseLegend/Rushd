# CLAUDE.md

Guidance for Claude Code when working in this repository.
Keep under 200 lines. Niche rules go in `.claude/rules/`.

## Project

Rushd — self-hosted web app, Module 1: partner-selection self-assessment
for Muslims, delivered as a guided conversation via the Claude API.
Target users: Amr + ~5 close friends. Not a public product.

## Stack (fixed — do not relitigate)

- **Claude API** (`claude-sonnet-5`) — assessment conversation + extraction
- **SQLite** — profiles and session state (`data/rushd.db`)
- **Flask** — web UI (`webapp/app.py`)
- **Invite-link auth** — no user accounts, known users only
- **Docker** — deployment on owner's infrastructure (Step 5)
- **Scale**: 2–5 users, occasional use — do not over-engineer

## Commands

```bash
cp .env.example .env          # one-time: add ANTHROPIC_API_KEY + FLASK_SECRET_KEY
python3 assessment/build_rubric.py   # one-time, re-run if transcripts change
python3 assessment/run_assessment.py # CLI assessment (dev/testing)
python3 webapp/app.py                # dev server
```

## Build Status — Phase 3

One step at a time. Confirm the done-condition before starting the next.

| # | Step | Status | Done-condition |
|---|------|--------|----------------|
| 1 | Data layer | ✅ Done | Can write/read a profile record |
| 2 | Assessment engine | ✅ Done | CLI produces a real 14-rating profile |
| 3 | Web app (auth + chat UI) | ✅ Done | Full browser flow verified end-to-end; prompt caching live |
| 4 | Save + view own results | 🔄 **NEXT** | User hits their invite link on a new browser/device and sees their completed profile instead of starting over |
| 5 | Deploy + back up | 🔲 Pending | Survives reboot; DB has a restore path |

**Comparison view (two profiles side-by-side): explicitly deferred. Do not
scope, design, or ask about it. Amr will open that phase when ready.**

## Hard Rules

- One step at a time — confirm done-condition before moving on
- Commit every working chunk with a clear message before moving on
- No migrations framework — apply schema changes to dev DB directly
- No managed/cloud DB, no serverless, no external auth services
- Verify Claude API/SDK specifics from current docs before stating as fact
- Never state a step is done without an end-to-end verification

## Deferred Issues (address at the step noted)

- `SESSION_COOKIE_SECURE` + `SameSite` not explicitly set — fix in Step 5 (HTTPS context)
- Null-profile template guard added in Step 3 close — known, acceptable at this user count

## Backlog (not in scope for any current step)

- Profile export: standard template for user to download their saved profile
- Kafā'ah content: transcript presents four dimensions as flat list; scholarly
  nuance (deen-only is binding, rest recommended) deferred pending more source material
