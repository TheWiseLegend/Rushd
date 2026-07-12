#!/usr/bin/env bash
# Copies data/rushd.db to a timestamped backup file alongside it.
# To restore: stop the container, then run
#   cp data/rushd.db.backup-<timestamp> data/rushd.db
# and start the container again.
set -euo pipefail

cd "$(dirname "$0")"

SRC="data/rushd.db"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
DEST="data/rushd.db.backup-${TIMESTAMP}"

if [ ! -f "$SRC" ]; then
  echo "No DB found at $SRC - nothing to back up."
  exit 1
fi

cp "$SRC" "$DEST"
echo "Backed up $SRC -> $DEST"
