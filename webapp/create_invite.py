"""Mints an invite token for a person and prints their invite link.

Run with: python3 webapp/create_invite.py "Person Name" [base_url]
base_url defaults to http://localhost:5000.
"""

import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "assessment"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import db


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 webapp/create_invite.py "Person Name" [base_url]')
        sys.exit(1)

    person_label = sys.argv[1]
    base_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5000"

    token = secrets.token_urlsafe(24)
    conn = db.get_conn()
    try:
        conn.execute(
            "INSERT INTO invite_tokens (token, person_label) VALUES (?, ?)",
            (token, person_label),
        )
        conn.commit()
    finally:
        conn.close()

    print(f"Invite link for {person_label}: {base_url}/invite/{token}")


if __name__ == "__main__":
    main()
