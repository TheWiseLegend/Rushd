# Rushd

Rushd is a self-reflection tool for Muslims thinking about partner selection,
grounded in the مودة course. Module 1 is a guided, conversational
self-assessment — you talk with an AI about your patterns and what you look
for in a partner, and it produces a private profile with ratings and
justifications. This is a personal project for Amr and a small circle of
close friends, not a public product.

## Prerequisites

- Docker Desktop installed and running
- A WSL2 terminal
- An Anthropic API key
- An ngrok account + authtoken (only needed if you're sharing the app with
  friends outside your own machine)

## First-time setup

1. Clone the repo.
2. Copy the env template and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set `ANTHROPIC_API_KEY` and `FLASK_SECRET_KEY`.
3. Build the assessment rubric (one-time; re-run only if the source
   transcripts change):
   ```bash
   python3 assessment/build_rubric.py
   ```
4. Build the Docker image:
   ```bash
   docker compose build
   ```

## Running the app

```bash
docker compose up -d
```

The app is now at `http://localhost:5000`.

```bash
docker compose down        # stop and remove the container
docker compose logs -f     # follow app logs
```

## Generating invite links

There are no user accounts — access is by personal invite link only. To add
a person and get their link:

```bash
python3 webapp/create_invite.py "Their Name"
```

This mints a token, stores it in the database, and prints something like:

```
Invite link for Their Name: http://localhost:5000/invite/<token>
```

If you're sharing over ngrok, pass the ngrok base URL as a second argument
instead of editing the output by hand:

```bash
python3 webapp/create_invite.py "Their Name" https://your-ngrok-url.ngrok-free.dev
```

Each link only works for the person it was minted for, and it's reusable —
see "Sharing with friends" below for how it behaves on repeat visits.

## Sharing with friends (ngrok)

The app only runs on `localhost`. ngrok opens a temporary public HTTPS
tunnel to it so a friend on their own device can reach it — it forwards
traffic in, it doesn't serve the app itself. **ngrok must be running at the
same time as the Docker container**, not instead of it.

One-time setup (already done on this machine):

```bash
ngrok config add-authtoken <token>
```

Get `<token>` from your ngrok dashboard. You won't need to run this again
unless ngrok's local config gets wiped.

Each time you want to share:

1. Make sure the app is up: `docker compose up -d`
2. Start the tunnel:
   ```bash
   ngrok http 5000
   ```
3. Copy the `https://...ngrok-free.dev` URL it prints.
4. Generate that person's invite link with the ngrok URL as the base (see
   above), or take an existing `/invite/<token>` and append it to the ngrok
   URL.
5. Send them the full link. Close the `ngrok http 5000` terminal when you're
   done sharing — the URL stops working as soon as the tunnel closes.

### How friends see their completed profile

The same invite link works every time. First visit takes them through the
assessment conversation; once it's done, revisiting that exact link — from
any device, any time — goes straight to their saved result instead of
starting over.

## Backup and restore

Back up:

```bash
./backup.sh
```

Copies `data/rushd.db` to `data/rushd.db.backup-<timestamp>`.

Restore:

```bash
docker compose down
cp data/rushd.db.backup-<timestamp> data/rushd.db
docker compose up -d
```

(Stop the app first so nothing writes to the DB mid-copy.)

## After a Windows reboot

`restart: always` in `docker-compose.yml` means Docker Desktop brings the
container back up automatically — you shouldn't need to run `docker compose
up -d` again yourself. If you were sharing externally, the ngrok tunnel does
**not** survive a reboot — just start a new one:

```bash
ngrok http 5000
```
