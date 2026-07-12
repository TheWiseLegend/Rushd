"""Minimal Flask web app wrapping the assessment/ conversation + extraction
engine behind HTTP routes.

Stage 1 scope: backend routes only, JSON in/out - no browser chat UI yet
(that's Stage 2). Auth is real (invite-link tokens, session-scoped
ownership checks) because the routes below can't be tested without it.

Run with: python3 webapp/app.py
Requires ANTHROPIC_API_KEY and FLASK_SECRET_KEY in .env (see .env.example).
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, session

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "assessment"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

load_dotenv(BASE_DIR / ".env")

import db
import engine
from system_prompt import build_conversation_system_prompt

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET_KEY"]

_client = None


def get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        _client = engine.get_client(api_key)
    return _client


def _load_active_session():
    """Returns (convo, None) or (None, (response, status)) - the ownership
    check lives in db.load_conversation_session, which filters on session_id
    AND the person_label from this authenticated session, never session_id alone.
    """
    person_label = session.get("person_label")
    if not person_label:
        return None, (jsonify(error="Not authenticated - visit your invite link first."), 401)

    session_id = session.get("conversation_session_id")
    if not session_id:
        return None, (jsonify(error="No active conversation - POST /start first."), 400)

    convo = db.load_conversation_session(session_id, person_label)
    if convo is None:
        return None, (jsonify(error="Conversation session not found."), 404)

    return convo, None


@app.route("/invite/<token>")
def invite(token):
    person_label = db.validate_invite_token(token)
    if person_label is None:
        return "Invalid or unknown invite link.", 404
    session["person_label"] = person_label
    session.pop("conversation_session_id", None)
    return f"Welcome, {person_label}. POST /start with {{'profile_language': 'ar'|'en'}} to begin."


@app.route("/start", methods=["POST"])
def start():
    person_label = session.get("person_label")
    if not person_label:
        return jsonify(error="Not authenticated - visit your invite link first."), 401

    body = request.get_json(silent=True) or {}
    profile_language = body.get("profile_language")
    if profile_language not in ("ar", "en"):
        return jsonify(error="profile_language must be 'ar' or 'en'"), 400

    system_prompt = build_conversation_system_prompt(profile_language)
    assistant_text, messages = engine.send_turn(get_client(), system_prompt, engine.initial_messages())

    session_id = db.create_conversation_session(person_label, profile_language, messages)
    session["conversation_session_id"] = session_id

    return jsonify(assistant_message=assistant_text, status="active")


@app.route("/message", methods=["POST"])
def message():
    convo, err = _load_active_session()
    if err:
        return err
    if convo["status"] != "active":
        return jsonify(error="This conversation has already ended."), 400

    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify(error="text is required"), 400

    system_prompt = build_conversation_system_prompt(convo["profile_language"])
    assistant_text, messages = engine.send_turn(get_client(), system_prompt, convo["messages"], text)
    db.update_conversation_session(convo["session_id"], convo["person_label"], messages, status="active")

    return jsonify(assistant_message=assistant_text, status="active")


@app.route("/done", methods=["POST"])
def done():
    convo, err = _load_active_session()
    if err:
        return err
    if convo["status"] != "active":
        return jsonify(error="This conversation has already ended."), 400

    profile = engine.run_extraction(
        get_client(), convo["messages"], convo["profile_language"], convo["person_label"]
    )
    profile_id = engine.save_profile_to_db(profile)
    db.update_conversation_session(convo["session_id"], convo["person_label"], convo["messages"], status="done")

    return jsonify(profile=profile, profile_id=profile_id, status="done")


if __name__ == "__main__":
    app.run(debug=True)
