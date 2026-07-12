"""Minimal Flask web app wrapping the assessment/ conversation + extraction
engine behind a browser chat UI. Function over form - server-rendered pages,
no JavaScript, one message per page load. That's fine for occasional use by
2-5 people.

Run with: python3 webapp/app.py
Requires ANTHROPIC_API_KEY and FLASK_SECRET_KEY in .env (see .env.example).
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for

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


def _load_own_session():
    """Returns the caller's conversation_sessions row, or None if not
    authenticated / no active session / the session doesn't belong to them.
    The ownership check itself lives in db.load_conversation_session, which
    filters on session_id AND person_label together, never session_id alone.
    """
    person_label = session.get("person_label")
    session_id = session.get("conversation_session_id")
    if not person_label or not session_id:
        return None
    return db.load_conversation_session(session_id, person_label)


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/invite/<token>")
def invite(token):
    person_label = db.validate_invite_token(token)
    if person_label is None:
        return render_template("invite_error.html"), 404
    session["person_label"] = person_label
    session.pop("conversation_session_id", None)

    profile_id = db.get_latest_profile_id(person_label)
    if profile_id is not None:
        profile = db.get_profile_with_ratings(profile_id, person_label)
        return render_template("result.html", profile=profile)

    return redirect(url_for("start"))


@app.route("/start", methods=["GET", "POST"])
def start():
    person_label = session.get("person_label")
    if not person_label:
        return redirect(url_for("landing"))

    # Already mid-conversation (or just finished) - don't start a second one.
    if session.get("conversation_session_id"):
        return redirect(url_for("chat"))

    if request.method == "GET":
        return render_template("start.html", person_label=person_label)

    profile_language = request.form.get("profile_language")
    if profile_language not in ("ar", "en"):
        return render_template("start.html", person_label=person_label, error="Please choose a language."), 400

    gender = request.form.get("gender")
    if gender not in ("male", "female"):
        return render_template("start.html", person_label=person_label, error="Please choose a gender."), 400

    age_raw = request.form.get("age")
    try:
        age = int(age_raw)
        if age <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return render_template("start.html", person_label=person_label, error="Please enter a valid age."), 400

    system_prompt = build_conversation_system_prompt(profile_language, age, gender)
    _, messages = engine.send_turn(get_client(), system_prompt, engine.initial_messages())

    session_id = db.create_conversation_session(person_label, profile_language, messages, age, gender)
    session["conversation_session_id"] = session_id

    return redirect(url_for("chat"))


@app.route("/chat")
def chat():
    convo = _load_own_session()
    if convo is None:
        return redirect(url_for("start"))

    if convo["status"] == "done":
        profile = db.get_profile_with_ratings(convo["profile_id"], convo["person_label"])
        return render_template("result.html", profile=profile)

    visible_messages = [m for m in convo["messages"] if m["content"] != engine.SESSION_START_TOKEN]
    return render_template("chat.html", messages=visible_messages)


@app.route("/message", methods=["POST"])
def message():
    convo = _load_own_session()
    if convo is None:
        return redirect(url_for("start"))
    if convo["status"] != "active":
        return redirect(url_for("chat"))

    text = (request.form.get("text") or "").strip()
    if not text:
        visible_messages = [m for m in convo["messages"] if m["content"] != engine.SESSION_START_TOKEN]
        return render_template("chat.html", messages=visible_messages, error="Please type something first."), 400

    system_prompt = build_conversation_system_prompt(convo["profile_language"], convo["age"], convo["gender"])
    _, messages = engine.send_turn(get_client(), system_prompt, convo["messages"], text)
    db.update_conversation_session(convo["session_id"], convo["person_label"], messages, status="active")

    return redirect(url_for("chat"))


@app.route("/done", methods=["POST"])
def done():
    convo = _load_own_session()
    if convo is None:
        return redirect(url_for("start"))
    if convo["status"] != "active":
        return redirect(url_for("chat"))

    # Atomic claim, before the (slow) API call: only the request that actually
    # flips active -> done gets to run extraction. A concurrent /done (double
    # submit) sees rowcount 0 and bails out instead of extracting twice.
    claimed = db.update_conversation_session(
        convo["session_id"], convo["person_label"], convo["messages"], status="done"
    )
    if claimed == 0:
        return redirect(url_for("chat"))

    try:
        profile = engine.run_extraction(
            get_client(), convo["messages"], convo["profile_language"], convo["person_label"]
        )
        profile_id = engine.save_profile_to_db(profile)
        db.set_profile_id(convo["session_id"], convo["person_label"], profile_id)
    except Exception:
        app.logger.exception("Profile extraction failed for session %s", convo["session_id"])
        db.update_conversation_session(
            convo["session_id"], convo["person_label"], convo["messages"], status="active"
        )
        visible_messages = [m for m in convo["messages"] if m["content"] != engine.SESSION_START_TOKEN]
        return render_template(
            "chat.html",
            messages=visible_messages,
            error="Something went wrong generating your profile — your conversation is saved, please try again.",
        ), 500

    return redirect(url_for("chat"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
