# CLAUDE.md

Guidance for Claude Code when working in this repository.
Keep under 200 lines. Niche rules go in `.claude/rules/`.

## Project

Rushd — self-hosted web app, Module 1: partner-selection self-assessment
for Muslims, delivered as a guided conversation via the Claude API.
Target users: Amr + ~5 close friends. Not a public product.

## Stack (fixed — do not relitigate)

- **Claude API** — model strings set in `assessment/engine.py` (verify against current Anthropic docs before changing, especially at Step 7) — assessment conversation + extraction
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

### Docker (Step 5 — deploy)

```bash
docker compose build       # build the image (rerun after code changes)
docker compose up -d       # start the container in the background
docker compose down        # stop and remove the container
docker compose logs -f     # follow app logs
```

`restart: always` in `docker-compose.yml` means Docker Desktop brings the
container back up automatically after a Windows reboot. `data/` is mounted
as a volume, so `data/rushd.db` lives on the host and survives container
rebuilds. `.env` is never copied into the image (see `.dockerignore`) — it's
injected at runtime via `env_file` in `docker-compose.yml`.

### Backup / restore

```bash
./backup.sh    # copies data/rushd.db -> data/rushd.db.backup-<timestamp>
```

To restore: stop the container (`docker compose down`), run
`cp data/rushd.db.backup-<timestamp> data/rushd.db`, then start it again
(`docker compose up -d`).

### Sharing (ngrok)

Not a project dependency — just how Amr shares the app with friends
without deploying it anywhere public. See README.md for the full flow.

```bash
ngrok http 5000          # run alongside docker compose up -d, not instead of it
```

One-time setup (already done on this machine):
`ngrok config add-authtoken <token>`.

## Build Status — Phase 3 (complete)

| # | Step | Status | Done-condition |
|---|------|--------|----------------|
| 1 | Data layer | ✅ Done | Can write/read a profile record |
| 2 | Assessment engine | ✅ Done | CLI produces a real 14-rating profile |
| 3 | Web app (auth + chat UI) | ✅ Done | Full browser flow verified end-to-end; prompt caching live |
| 4 | Save + view own results | ✅ Done | User hits their invite link on a new browser/device and sees their completed profile instead of starting over |
| 5 | Deploy + back up | ✅ Done | Survives reboot; DB has a restore path |

**Comparison view (two profiles side-by-side): explicitly deferred. Do not
scope, design, or ask about it. Amr will open that phase when ready.**

## Build Status — Phase 3.5 (v2.0 Refinements) — COMPLETE

One step at a time. Confirm the done-condition before starting the next.
Steps below IN PROGRESS or later are not yet implemented — do not implement
a step ahead of its turn.

| # | Step | Status | Done-condition |
|---|------|--------|----------------|
| 1 | System prompt quality (no terminology leakage, interpretation over summary) | ✅ Done | Committed |
| 2 | Personal info intake (age/gender on `/start`) | ✅ Done | Age/gender captured, stored, and reach the model from message 1 |
| 3 | Loading state (disable Submit on click, inline "...") | ✅ Done | Pure HTML/CSS/minimal JS, no framework |
| 4 | Rating justifications (`justification` field on `profile_ratings` + tool schema + result.html + rebuilt rubric) | ✅ Done | — |
| 5 | Result page redesign (grouped ratings, dimension descriptions, conversation-history toggle) | ✅ Done | — |
| 6 | Theme coverage indicator (explored themes shown in chat UI, not a percentage bar) | ✅ Done | — |
| 7 | Cost optimization (`send_turn` → claude-haiku, `run_extraction` stays on Sonnet, verify caching still active) | ✅ Done | — |

## Hard Rules

- One step at a time — confirm done-condition before moving on
- Never implement a step that isn't marked IN PROGRESS
- Commit every working chunk with a clear message before moving on
- No migrations framework — schema changes: `ALTER TABLE` directly on
  `data/rushd.db`, update `db/schema.sql` to match, nullable columns only
  (protects existing rows)
- No managed/cloud DB, no serverless, no external auth services
- Verify Claude API/SDK specifics from current docs before stating as fact
  (especially model strings — check current Anthropic model names before
  using any in code, particularly for Step 7)
- Never state a step is done without an end-to-end verification

## Deferred Issues (address at the step noted)

- `SESSION_COOKIE_SECURE` + `SameSite` not set — deferred until HTTPS is added (no current step assigned)
- Null-profile template guard added in Step 3 close — known, acceptable at this user count

## Backlog (not in scope for any current step)

- Profile export: standard template for user to download their saved profile
- Kafā'ah content: transcript presents four dimensions as flat list; scholarly
  nuance (deen-only is binding, rest recommended) deferred pending more source material
