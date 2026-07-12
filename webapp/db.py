"""SQLite helpers for the web app's invite tokens and conversation sessions.
Uses the same data/rushd.db as assessment/engine.py's profile writes.

Every conversation_sessions query filters on session_id AND person_label
together - a session_id alone is never trusted, so one authenticated
person's cookie can't be used to read or write another person's
in-progress conversation.
"""

import json
import sqlite3
import uuid

from engine import DB_PATH, SCHEMA_PATH


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def validate_invite_token(token: str) -> str | None:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT person_label FROM invite_tokens WHERE token = ?", (token,)
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE invite_tokens SET last_used_at = datetime('now') WHERE token = ?",
            (token,),
        )
        conn.commit()
        return row["person_label"]
    finally:
        conn.close()


def create_conversation_session(person_label: str, profile_language: str, messages: list) -> str:
    session_id = uuid.uuid4().hex
    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO conversation_sessions
                (session_id, person_label, profile_language, messages_json, status)
            VALUES (?, ?, ?, ?, 'active')
            """,
            (session_id, person_label, profile_language, json.dumps(messages)),
        )
        conn.commit()
        return session_id
    finally:
        conn.close()


def load_conversation_session(session_id: str, person_label: str) -> dict | None:
    conn = get_conn()
    try:
        row = conn.execute(
            """
            SELECT session_id, person_label, profile_language, messages_json, status
            FROM conversation_sessions
            WHERE session_id = ? AND person_label = ?
            """,
            (session_id, person_label),
        ).fetchone()
        if row is None:
            return None
        return {
            "session_id": row["session_id"],
            "person_label": row["person_label"],
            "profile_language": row["profile_language"],
            "messages": json.loads(row["messages_json"]),
            "status": row["status"],
        }
    finally:
        conn.close()


def update_conversation_session(session_id: str, person_label: str, messages: list, status: str) -> None:
    conn = get_conn()
    try:
        conn.execute(
            """
            UPDATE conversation_sessions
            SET messages_json = ?, status = ?, updated_at = datetime('now')
            WHERE session_id = ? AND person_label = ?
            """,
            (json.dumps(messages), status, session_id, person_label),
        )
        conn.commit()
    finally:
        conn.close()
