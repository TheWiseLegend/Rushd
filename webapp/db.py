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
            SELECT session_id, person_label, profile_language, messages_json, status, profile_id
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
            "profile_id": row["profile_id"],
        }
    finally:
        conn.close()


def update_conversation_session(session_id: str, person_label: str, messages: list, status: str) -> int:
    """Returns the number of rows updated.

    For status='done' this is a compare-and-swap: the WHERE clause requires the
    row to currently be 'active', so if two /done requests race, only one gets
    rowcount=1 and is allowed to run extraction - the loser sees rowcount=0 and
    bails out instead of extracting twice. profile_id is attached afterward via
    set_profile_id(), once extraction succeeds, since it isn't known yet at the
    point this flip needs to happen (before the API call).
    """
    conn = get_conn()
    try:
        if status == "done":
            cur = conn.execute(
                """
                UPDATE conversation_sessions
                SET status = 'done', messages_json = ?, updated_at = datetime('now')
                WHERE session_id = ? AND person_label = ? AND status = 'active'
                """,
                (json.dumps(messages), session_id, person_label),
            )
        else:
            cur = conn.execute(
                """
                UPDATE conversation_sessions
                SET messages_json = ?, status = ?, updated_at = datetime('now')
                WHERE session_id = ? AND person_label = ?
                """,
                (json.dumps(messages), status, session_id, person_label),
            )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def set_profile_id(session_id: str, person_label: str, profile_id: int) -> None:
    """Attaches the extracted profile to a session already flipped to 'done' by
    update_conversation_session's compare-and-swap. Only the single request that
    won that CAS ever reaches here, so no further guard is needed."""
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE conversation_sessions SET profile_id = ?, updated_at = datetime('now') "
            "WHERE session_id = ? AND person_label = ?",
            (profile_id, session_id, person_label),
        )
        conn.commit()
    finally:
        conn.close()


def get_latest_profile_id(person_label: str) -> int | None:
    """Looks up an existing completed profile by person_label alone - used by
    /invite, where a new browser/device has no session cookie yet to look up
    a profile_id through."""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT id FROM profiles WHERE person_label = ? ORDER BY id DESC LIMIT 1",
            (person_label,),
        ).fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


def get_profile_with_ratings(profile_id: int, person_label: str) -> dict | None:
    """Scoped by person_label too, for the same reason conversation_sessions is -
    a profile_id from a session cookie should never let one person read another's profile."""
    conn = get_conn()
    try:
        profile_row = conn.execute(
            """
            SELECT id, person_label, self_awareness_summary, strengths, weaknesses, what_to_look_for
            FROM profiles
            WHERE id = ? AND person_label = ?
            """,
            (profile_id, person_label),
        ).fetchone()
        if profile_row is None:
            return None
        rating_rows = conn.execute(
            "SELECT dimension_key, dimension_label, rating FROM profile_ratings WHERE profile_id = ?",
            (profile_id,),
        ).fetchall()
        return {
            "self_awareness_summary": profile_row["self_awareness_summary"],
            "strengths": profile_row["strengths"],
            "weaknesses": profile_row["weaknesses"],
            "what_to_look_for": profile_row["what_to_look_for"],
            "ratings": [dict(r) for r in rating_rows],
        }
    finally:
        conn.close()
