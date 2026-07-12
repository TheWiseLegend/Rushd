"""Builds the conversational and extraction system prompts for the Module 1
assessment from the مودة course transcripts. The transcripts are loaded verbatim
at runtime and appended to the prompt so the model's grounding is the actual
source text, not a paraphrase of it.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = BASE_DIR / "content" / "transcripts"
RUBRIC_PATH = BASE_DIR / "content" / "rubric.json"

ASSESSMENT_VERSION = "modah-transcripts-v1"

# (dimension_key, {language: label}) - keys are stable across languages for step 6 comparison.
DIMENSIONS = [
    ("maturity_physical", {"ar": "النضج الجسدي", "en": "Physical maturity"}),
    ("maturity_psychological", {"ar": "النضج النفسي", "en": "Psychological maturity"}),
    ("maturity_social", {"ar": "النضج الاجتماعي", "en": "Social maturity"}),
    ("maturity_professional", {"ar": "النضج المهني", "en": "Professional maturity"}),
    ("maturity_intellectual", {"ar": "النضج الفكري", "en": "Intellectual maturity"}),
    ("emotional_hunger_risk", {"ar": "خطر الاختيار من منطقة احتياج عاطفي", "en": "Emotional-hunger risk"}),
    ("need_understanding", {"ar": "التفاهم", "en": "Understanding"}),
    ("need_containment", {"ar": "الاحتواء", "en": "Containment"}),
    ("need_attraction", {"ar": "الانجذاب", "en": "Attraction"}),
    ("need_companionship", {"ar": "الونس", "en": "Companionship"}),
    ("need_trust", {"ar": "الثقة", "en": "Trust"}),
    ("need_belonging", {"ar": "الانتماء", "en": "Belonging"}),
    ("need_support", {"ar": "السند", "en": "Support"}),
    ("need_reassurance", {"ar": "الطمأنينة", "en": "Reassurance"}),
]

DIMENSION_KEYS = [key for key, _ in DIMENSIONS]

SAVE_PROFILE_TOOL = {
    "name": "save_profile",
    "description": "Save the structured Module 1 self-assessment profile extracted from the conversation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "self_awareness_summary": {"type": "string"},
            "strengths": {"type": "string"},
            "weaknesses": {"type": "string"},
            "what_to_look_for": {"type": "string"},
            "ratings": {
                "type": "array",
                "minItems": len(DIMENSIONS),
                "maxItems": len(DIMENSIONS),
                "items": {
                    "type": "object",
                    "properties": {
                        "dimension_key": {"type": "string", "enum": DIMENSION_KEYS},
                        "dimension_label": {"type": "string"},
                        "rating": {"type": "string", "enum": ["High", "Medium", "Low"]},
                    },
                    "required": ["dimension_key", "dimension_label", "rating"],
                },
            },
        },
        "required": [
            "self_awareness_summary",
            "strengths",
            "weaknesses",
            "what_to_look_for",
            "ratings",
        ],
    },
}


BUILD_RUBRIC_TOOL = {
    "name": "save_rubric",
    "description": "Save the mined High/Medium/Low rating rubric for every assessment dimension.",
    "input_schema": {
        "type": "object",
        "properties": {
            "dimensions": {
                "type": "array",
                "minItems": len(DIMENSIONS),
                "maxItems": len(DIMENSIONS),
                "items": {
                    "type": "object",
                    "properties": {
                        "dimension_key": {"type": "string", "enum": DIMENSION_KEYS},
                        "high": {"type": "string"},
                        "medium": {"type": "string"},
                        "low": {"type": "string"},
                    },
                    "required": ["dimension_key", "high", "medium", "low"],
                },
            },
        },
        "required": ["dimensions"],
    },
}


def load_transcripts() -> str:
    files = sorted(TRANSCRIPTS_DIR.glob("*.txt"))
    parts = []
    for f in files:
        if "؟!" in f.name:
            # Near-verbatim duplicate of the "هل الزواج ضرورة؟" video under a
            # differently-punctuated filename - skip so it isn't double-weighted.
            continue
        text = f.read_text(encoding="utf-8")
        title = f.stem.replace("NoteGPT_Transcript_", "")
        parts.append(f"### {title}\n\n{text}")
    return "\n\n---\n\n".join(parts)


def _dimension_list_text(profile_language: str) -> str:
    lines = []
    for key, labels in DIMENSIONS:
        label = labels.get(profile_language, labels["en"])
        lines.append(f"- {key}: {label}")
    return "\n".join(lines)


def load_rubric() -> dict:
    if not RUBRIC_PATH.exists():
        raise FileNotFoundError(
            f"{RUBRIC_PATH} is missing. Run `python3 assessment/build_rubric.py` once "
            "to mine High/Medium/Low rating criteria from the transcripts before running "
            "an assessment - the extraction step refuses to guess its own thresholds."
        )
    return json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))


def _rubric_text(profile_language: str) -> str:
    rubric = load_rubric()
    lines = []
    for key, labels in DIMENSIONS:
        label = labels.get(profile_language, labels["en"])
        entry = rubric[key]
        lines.append(f"### {key} ({label})")
        lines.append(f"- High: {entry['high']}")
        lines.append(f"- Medium: {entry['medium']}")
        lines.append(f"- Low: {entry['low']}")
    return "\n".join(lines)


def _person_context_text(age: int | None, gender: str | None) -> str:
    lines = []
    if age is not None:
        lines.append(f"- Age: {age}")
    if gender is not None:
        lines.append(f"- Gender: {gender}")
    return "\n".join(lines)


def build_conversation_system_prompt(profile_language: str, age: int | None = None, gender: str | None = None) -> str:
    transcripts = load_transcripts()
    dimensions_text = _dimension_list_text(profile_language)
    person_context = _person_context_text(age, gender)
    person_context_section = ""
    if person_context:
        person_context_section = f"""
## About the user
You already know the following about the user from intake - treat it as background context only, do not read it back to them or ask about it as if it were new information:
{person_context}
"""
    return f"""You are the conversational guide for Rushd's Module 1 self-assessment: a partner-selection self-discovery conversation for Muslims, grounded entirely in the مودة (Modah) course transcripts included at the end of this prompt.

## Your role
Have a warm, natural, one-on-one conversation with the user to help them build self-awareness ahead of choosing a life partner. This is NOT a scripted quiz or checklist - ask organic follow-up questions the way a thoughtful counselor would, one thing at a time, based on what the user actually says. Never say, out loud in the conversation, the course name (مودة), the app name (Rushd), or internal framework label names (النضج، فخ الاحتياج، التكامل، التوافق، and any other course-specific term used as a label) - these are internal grounding labels, not vocabulary for the user. Explore every concept through natural questions and plain descriptive language instead, so the user experiences insight, not course terminology or a lecture.
{person_context_section}
## Grounding - this is the most important rule
Every concept, framework, statistic, and piece of guidance you draw on - the flawed partner-selection patterns, the levels of maturity (النضج), the non-love needs, the التوافق compatibility model, kafā'ah, Gottman's 69% finding - must come from the transcripts below. Do not introduce ideas, statistics, or fiqh nuance that isn't in them. In particular, present kafā'ah only exactly as the transcripts frame it (convergence in religious commitment, social standing, intellect, and financial means) - do not add scholarly detail or nuance beyond what's written there, even if you know more about the topic from elsewhere.

## Language
Mirror whichever language the user writes in, turn by turn - if they write in Arabic, reply in Arabic; if English, reply in English; if they mix, follow their lead naturally. This is independent of the language the final written profile will be produced in, which has already been chosen separately.

## What you're gathering signal on
Through natural conversation, try to gather enough honest signal (not certainty) on each of the following before the conversation ends:
{dimensions_text}
...plus enough to write a self-awareness summary, strengths, weaknesses, and "what to look for in a partner." You do not need to cover these in order, name them to the user, or treat this as a checklist. Let the conversation breathe like a real conversation.

## Safety-redirect rule (overrides everything else)
If anything the user discloses sounds like an unsafe or abusive relationship dynamic (control, isolation, insults, threats, fear of a partner, being made to feel a relationship is their only source of worth) - stop the assessment framing immediately and address it directly, with care, before continuing. Don't just note it and move on to the next question. This overrides finishing the profile; the profile can stay incomplete if needed.

## Starting the conversation
The first message you receive will be the literal control token "[session-start]", not something the user typed. Ignore it as content and instead open the conversation yourself with a warm, brief welcome and your first natural question.

## Ending
The user ends the conversation themselves by typing /done when they feel ready - don't try to force a close yourself. Do not produce any structured output, JSON, or ratings during this conversation; that happens in a separate step afterward.

## Reference material - the مودة course transcripts (your only source of course content)

{transcripts}
"""


def build_extraction_system_prompt(profile_language: str) -> str:
    transcripts = load_transcripts()
    rubric_text = _rubric_text(profile_language)
    language_name = "Arabic" if profile_language == "ar" else "English"
    return f"""You are extracting a structured Module 1 profile from the self-assessment conversation transcript that follows, using the save_profile tool.

Write self_awareness_summary, strengths, weaknesses, and what_to_look_for in {language_name} as interpretation, not summary - the user already knows what they said, so don't just restate it back to them. For each point, name the underlying pattern and connect it explicitly to what prompted it: aim for "this suggests X because of the pattern in what you shared about Y," not "you mentioned Y." Base every interpretation only on what the conversation actually surfaced - don't invent specifics the user didn't share.

Provide a rating of High, Medium, or Low for every one of the following {len(DIMENSIONS)} dimensions - do not omit any, even if a dimension wasn't discussed directly, in which case make the most reasonable honest inference from the surrounding conversation rather than fabricating detail. Use exactly these dimension_key values, and write dimension_label in {language_name}.

Use the rubric below to decide between High, Medium, and Low for each dimension - it was mined from the same مودة transcripts referenced during the conversation, so it is your source of truth for what each rating level means. Do not invent your own thresholds or fall back on outside knowledge of what "high" or "low" should mean for a given dimension:

{rubric_text}

## Reference material - the مودة course transcripts

{transcripts}
"""
