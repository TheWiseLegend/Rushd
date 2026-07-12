"""Interactive terminal script for the Module 1 assessment conversation.

Run with: python3 assessment/run_assessment.py

Requires ANTHROPIC_API_KEY in a .env file at the repo root (see .env.example).
This script loads it only into its own process - it is never exported to the shell.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from system_prompt import (
    ASSESSMENT_VERSION,
    SAVE_PROFILE_TOOL,
    build_conversation_system_prompt,
    build_extraction_system_prompt,
)

MODEL = "claude-sonnet-5"
SESSION_START_TOKEN = "[session-start]"


def ask_profile_language() -> str:
    while True:
        answer = input("Which language should your final profile be written in? [ar/en]: ").strip().lower()
        if answer in ("ar", "en"):
            return answer
        print("Please type 'ar' or 'en'.")


def ask_person_label() -> str:
    while True:
        answer = input("What name should this profile be saved under?: ").strip()
        if answer:
            return answer
        print("Please enter a name.")


def extract_text(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


def run_conversation(client, system_prompt: str) -> list:
    messages = [{"role": "user", "content": SESSION_START_TOKEN}]
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        assistant_text = extract_text(response)
        messages.append({"role": "assistant", "content": assistant_text})
        print(f"\n{assistant_text}\n")

        user_input = input(">> ").strip()
        if user_input == "/done":
            return messages
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})


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


def main():
    load_dotenv(BASE_DIR / ".env")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    profile_language = ask_profile_language()
    person_label = ask_person_label()
    system_prompt = build_conversation_system_prompt(profile_language)

    print("\nStarting the assessment conversation. Type /done at any point when you're ready to see your profile.\n")

    try:
        messages = run_conversation(client, system_prompt)
    except KeyboardInterrupt:
        print("\nInterrupted - no profile produced.")
        sys.exit(0)

    print("\nGenerating your profile...\n")
    profile = run_extraction(client, messages, profile_language, person_label)

    print(json.dumps(profile, ensure_ascii=False, indent=2))

    save = input("\nSave this profile to a local JSON file? [y/N]: ").strip().lower()
    if save == "y":
        out_dir = BASE_DIR / "output"
        out_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_label = "".join(c if c.isalnum() else "_" for c in person_label)
        out_path = out_dir / f"profile_{safe_label}_{timestamp}.json"
        out_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
