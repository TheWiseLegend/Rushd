#!/usr/bin/env bash
# Applies db/schema.sql to data/rushd.db (creates the file if it doesn't exist yet).
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p data
python3 -c "
import sqlite3
conn = sqlite3.connect('data/rushd.db')
conn.executescript(open('db/schema.sql').read())
conn.commit()
conn.close()
print('Applied db/schema.sql to data/rushd.db')
"
