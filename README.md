# Rushd

Personal tool, not a public product. Notes for running and sharing it.

## Starting the app

```bash
docker compose up -d
```

Runs at `http://localhost:5000`. `restart: always` means Docker Desktop
brings it back up automatically after a Windows reboot — you shouldn't
need to run this again unless you've stopped it yourself.

## Stopping it

```bash
docker compose down
```

## Sharing with friends

The app only runs on `localhost` — ngrok opens a temporary public HTTPS
tunnel to it so a friend on their own device can reach it. **ngrok has to
be running at the same time as Docker** — it just forwards traffic in,
it doesn't serve the app itself.

1. Make sure the app is up: `docker compose up -d`
2. Start the tunnel:
   ```bash
   ngrok http 5000
   ```
3. Copy the `https://...ngrok-free.dev` URL it prints.
4. Mint an invite token for that person (if you haven't already):
   ```bash
   python3 webapp/create_invite.py "Their Name"
   ```
   This prints a link like `http://localhost:5000/invite/<token>` — take
   just the `/invite/<token>` part and append it to the ngrok URL, e.g.
   `https://churchless-brotherly-marsha.ngrok-free.dev/invite/<token>`.
5. Send them that link. Close the `ngrok http 5000` terminal when you're
   done sharing — the URL stops working as soon as the tunnel closes.

(One-time setup, already done on this machine: `ngrok config
add-authtoken <token>`, using the token from your ngrok dashboard. You
won't need to run this again unless ngrok's config gets wiped.)

### How friends see their completed profile

The same invite link works every time. First visit takes them through the
assessment conversation; once it's done, revisiting that exact link —
from any device, any time — goes straight to their saved result instead
of starting over.

## Backing up the database

```bash
./backup.sh
```

Copies `data/rushd.db` to `data/rushd.db.backup-<timestamp>`.

## Restoring from backup

```bash
docker compose down
cp data/rushd.db.backup-<timestamp> data/rushd.db
docker compose up -d
```

(Stop the app first so nothing writes to the DB mid-copy.)
