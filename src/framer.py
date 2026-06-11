# src/framer.py
# Layer 5: Frame Generator — Groq (Llama 3.3 70B)
#
# Groq is free, fast, no billing required.
# Llama 3.3 70B is a genuinely capable open-source model.
# Free tier: 14,400 requests/day, 30 requests/minute — plenty for HOF.

import os
import re
from dotenv import load_dotenv
from groq import Groq
from src.prompt import SYSTEM_PROMPT, build_user_message

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"


def generate_frame(story: dict) -> dict:
    """
    Generate a HOF debate frame using Llama 3.3 70B via Groq.
    Returns a parsed frame dict with all five sections.
    """
    user_message = build_user_message(story)

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_message}
            ],
            temperature=0.7,
            max_tokens=1200,
        )

        raw_text = response.choices[0].message.content

        if not raw_text:
            raise ValueError(f"Empty response for: {story.get('title', '')[:60]}")

        return parse_frame(raw_text)

    except Exception as e:
        raise RuntimeError(f"Frame generation failed: {e}") from e


def parse_frame(raw: str) -> dict:
    """Parse the five-section response into a structured dict."""
    frame = {
        "what_happened":  "",
        "why_it_matters": "",
        "core_tension":   "",
        "side_a":         "",
        "side_b":         "",
        "why_you":        "",
        "open_question":  "",
        "raw":            raw
    }

    frame["what_happened"]  = _extract(raw, "WHAT HAPPENED",                             "WHY IT MATTERS STRUCTURALLY")
    frame["why_it_matters"] = _extract(raw, "WHY IT MATTERS STRUCTURALLY",                "THE CORE TENSION")
    frame["core_tension"]   = _extract(raw, "THE CORE TENSION",                           "TWO SIDES")
    two_sides_block         = _extract(raw, "TWO SIDES",                                  "WHY YOU SPECIFICALLY")
    frame["why_you"]        = _extract(raw, "WHY YOU SPECIFICALLY SHOULD HAVE A POSITION", None)

    frame["side_a"]        = _extract_side(two_sides_block, "Side A")
    frame["side_b"]        = _extract_side(two_sides_block, "Side B")
    frame["open_question"] = _extract_question(frame["why_you"])

    for key in ["what_happened", "why_it_matters", "core_tension",
                "side_a", "side_b", "why_you", "open_question"]:
        if frame[key]:
            frame[key] = _clean_markdown(frame[key])

    return frame


def _extract(text: str, start_marker: str, end_marker: str | None) -> str:
    start_idx = text.find(start_marker)
    if start_idx == -1:
        start_idx = text.lower().find(start_marker.lower())
    if start_idx == -1:
        return ""

    content_start = _skip_separators(text, start_idx + len(start_marker))

    if end_marker is None:
        return text[content_start:].strip()

    end_idx = text.find(end_marker, content_start)
    if end_idx == -1:
        end_idx = text.lower().find(end_marker.lower(), content_start)
    if end_idx == -1:
        return text[content_start:].strip()

    return text[content_start:end_idx].strip()


def _skip_separators(text: str, pos: int) -> int:
    while pos < len(text) and text[pos] in ('-', '_', '─', '=', ' ', '\n', '\r', '*', '#'):
        pos += 1
    return pos


def _extract_side(block: str, label: str) -> str:
    clean   = re.sub(r'\*\*([^*]+)\*\*', r'\1', block)
    pattern = rf"(?i){re.escape(label)}[:\s]+(.*?)(?=Side\s+[AB][:\s]|$)"
    match   = re.search(pattern, clean, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _extract_question(text: str) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    for sentence in reversed(sentences):
        if sentence.strip().endswith("?"):
            return sentence.strip()
    return ""


def _clean_markdown(text: str) -> str:
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*',     r'\1', text)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    return text.strip()


def frame_quality_check(frame: dict) -> tuple[bool, list[str]]:
    """Quality gate before saving. Returns (passes, issues)."""
    issues = []

    if len(frame.get("what_happened",  "")) < 50:  issues.append("what_happened too short")
    if len(frame.get("why_it_matters", "")) < 60:  issues.append("why_it_matters too short")
    if len(frame.get("side_a",         "")) < 80:  issues.append("side_a too short")
    if len(frame.get("side_b",         "")) < 80:  issues.append("side_b too short")
    if not frame.get("open_question"):              issues.append("open question missing")

    tension = frame.get("core_tension", "")
    if not tension or "vs" not in tension.lower():
        issues.append("core_tension missing 'vs' format")

    len_a = len(frame.get("side_a", ""))
    len_b = len(frame.get("side_b", ""))
    if len_a > 0 and len_b > 0:
        ratio = max(len_a, len_b) / min(len_a, len_b)
        if ratio > 2.5:
            issues.append(f"sides imbalanced ({ratio:.1f}x)")

    banned = [
        "it is important", "it is crucial", "young people should",
        "it is clear that", "as an ai", "i cannot provide", "i must note"
    ]
    full_text = frame.get("raw", "").lower()
    for phrase in banned:
        if phrase in full_text:
            issues.append(f"banned phrase: '{phrase}'")

    return len(issues) == 0, issues