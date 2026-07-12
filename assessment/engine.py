"""Shared conversation + extraction engine used by both the CLI script
(run_assessment.py) and the web app - the actual turn-taking, profile
extraction, and DB write live here so neither caller reimplements them.
"""

import sqlite3
from pathlib import Path

from system_prompt import ASSESSMENT_VERSION, SAVE_PROFILE_TOOL, build_extraction_system_prompt

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "rushd.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"

MODEL = "claude-sonnet-5"
SESSION_START_TOKEN = "[session-start]"


def get_client(api_key: str):
    import anthropic

    return anthropic.Anthropic(api_key=api_key)


def extract_text(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


def initial_messages() -> list:
    return [{"role": "user", "content": SESSION_START_TOKEN}]


def send_turn(client, system_prompt: str, messages: list, user_text: str | None = None) -> tuple:
    """Appends user_text (if given), gets the assistant's reply, and appends that too.
    Pass user_text=None only for the very first call, to get the opening greeting."""
    messages = list(messages)
    if user_text is not None:
        messages.append({"role": "user", "content": user_text})

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=messages,
    )
    assistant_text = extract_text(response)
    messages.append({"role": "assistant", "content": assistant_text})
    return assistant_text, messages


def run_extraction(client, messages: list, profile_language: str, person_label: str) -> dict:
    extraction_system = build_extraction_system_prompt(profile_language)
    convo = list(messages)
    convo.append({"role": "user", "content": "Please now extract the structured profile using the save_profile tool."})

    response = client.messages.create(
        model=MODEL,
        max_tokens=3000,
        system=extraction_system,
        messages=convo,
        tools=[SAVE_PROFILE_TOOL],
        tool_choice={"type": "tool", "name": "save_profile"},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "save_profile":
            data = block.input
            break
    else:
        raise RuntimeError("Model did not return the expected save_profile tool call.")

    return {
        "person_label": person_label,
        "self_awareness_summary": data["self_awareness_summary"],
        "strengths": data["strengths"],
        "weaknesses": data["weaknesses"],
        "what_to_look_for": data["what_to_look_for"],
        "assessment_version": ASSESSMENT_VERSION,
        "ratings": data["ratings"],
    }


def save_profile_to_db(profile: dict) -> int:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        cur = conn.execute(
            """
            INSERT INTO profiles
                (person_label, self_awareness_summary, strengths, weaknesses, what_to_look_for, assessment_version)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                profile["person_label"],
                profile["self_awareness_summary"],
                profile["strengths"],
                profile["weaknesses"],
                profile["what_to_look_for"],
                profile["assessment_version"],
            ),
        )
        profile_id = cur.lastrowid
        conn.executemany(
            """
            INSERT INTO profile_ratings (profile_id, dimension_key, dimension_label, rating)
            VALUES (?, ?, ?, ?)
            """,
            [
                (profile_id, r["dimension_key"], r["dimension_label"], r["rating"])
                for r in profile["ratings"]
            ],
        )
        conn.commit()
        return profile_id
    finally:
        conn.close()
