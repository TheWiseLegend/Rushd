"""One-time build step: mines High/Medium/Low rating criteria for every
assessment dimension out of the مودة course transcripts, and caches the
result to content/rubric.json.

Run with: python3 assessment/build_rubric.py

This exists so the extraction step in run_assessment.py never has to invent
its own notion of what "High" vs "Low" means for a dimension - it reads the
same criteria mined here, which are grounded in the transcript text rather
than hand-written by the developer. Re-run this whenever the transcripts in
content/transcripts/ change.
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from system_prompt import (
    BUILD_RUBRIC_TOOL,
    DIMENSIONS,
    DIMENSION_KEYS,
    RUBRIC_PATH,
    load_transcripts,
)

MODEL = "claude-sonnet-5"

DIMENSION_LIST_TEXT = "\n".join(f"- {key}: {labels['en']}" for key, labels in DIMENSIONS)


def build_prompt() -> str:
    transcripts = load_transcripts()
    return f"""You are mining a High/Medium/Low rating rubric for a partner-selection self-assessment, using only the مودة course transcripts below.

For each of the following {len(DIMENSIONS)} dimensions, write one to two sentences each describing what a High, Medium, and Low rating would concretely look like in a person's conversational answers:
{DIMENSION_LIST_TEXT}

Rules:
- Base every High/Medium/Low description strictly on how the transcripts describe degrees, signs, or examples of that concept. Do not invent criteria, statistics, or nuance the transcripts don't support.
- Most of these transcripts describe concepts as poles (mature vs immature, secure vs emotionally hungry) rather than as an explicit three-tier scale. Where that's the case, describe High and Low from the poles the transcripts actually discuss, and describe Medium as the reasonable midpoint between them - and say so directly in the Medium text (e.g. "a middle ground between ... and ..., as neither extreme described in the material") so it reads as an interpolation, not a distinct tier the transcripts state outright.
- If a dimension genuinely isn't addressed in the transcripts in enough depth to distinguish three tiers at all, say that plainly in all three fields rather than fabricating specificity.
- Write in English regardless of what language the final assessment profile will later be produced in - this rubric is internal guidance for the extraction step, not user-facing text.

Use the save_rubric tool to report your answer, with exactly these dimension_key values: {", ".join(DIMENSION_KEYS)}.

## Reference material - the مودة course transcripts

{transcripts}
"""


def main():
    load_dotenv(BASE_DIR / ".env")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    print("Mining rating rubric from transcripts...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": build_prompt()}],
        tools=[BUILD_RUBRIC_TOOL],
        tool_choice={"type": "tool", "name": "save_rubric"},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "save_rubric":
            data = block.input
            break
    else:
        raise RuntimeError("Model did not return the expected save_rubric tool call.")

    rubric = {entry["dimension_key"]: entry for entry in data["dimensions"]}
    missing = set(DIMENSION_KEYS) - set(rubric.keys())
    if missing:
        raise RuntimeError(f"Model omitted dimensions from the rubric: {sorted(missing)}")

    ordered = {
        key: {
            "high": rubric[key]["high"],
            "medium": rubric[key]["medium"],
            "low": rubric[key]["low"],
        }
        for key in DIMENSION_KEYS
    }

    RUBRIC_PATH.write_text(json.dumps(ordered, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved rubric for {len(ordered)} dimensions to {RUBRIC_PATH}")


if __name__ == "__main__":
    main()
