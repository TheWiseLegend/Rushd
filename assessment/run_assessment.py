"""Interactive terminal script for the Module 1 assessment conversation.

Run with: python3 assessment/run_assessment.py

Requires ANTHROPIC_API_KEY in a .env file at the repo root (see .env.example).
This script loads it only into its own process - it is never exported to the shell.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine import DB_PATH, get_client, initial_messages, run_extraction, save_profile_to_db, send_turn
from system_prompt import build_conversation_system_prompt


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


def run_conversation(client, system_prompt: str) -> list:
    assistant_text, messages = send_turn(client, system_prompt, initial_messages())
    print(f"\n{assistant_text}\n")
    while True:
        user_input = input(">> ").strip()
        if user_input == "/done":
            return messages
        if not user_input:
            continue
        assistant_text, messages = send_turn(client, system_prompt, messages, user_input)
        print(f"\n{assistant_text}\n")


def main():
    load_dotenv(BASE_DIR / ".env")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    client = get_client(api_key)

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

    save = input("\nSave this profile to the database? [y/N]: ").strip().lower()
    if save == "y":
        profile_id = save_profile_to_db(profile)
        print(f"Saved to {DB_PATH} (profile id {profile_id})")


if __name__ == "__main__":
    main()
