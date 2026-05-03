"""
tpm_core.clarification - Clarification Loop (§ 7)
ref: MASTER_PLAN_v5.md § 7.3

Flow:
    user_request -> parse_intent (with confidence)
    if confidence >= MIN -> final_confirm -> done
    else -> generate clarification question -> wait user -> loop
"""
from __future__ import annotations

import logging
import re
from typing import Any

from tpm_core.llm import chat_json
from tpm_core.state import Intent

log = logging.getLogger(__name__)

# ============================================================
# Prompts (versioned - lives in .tpm_context/prompts/orchestrator/ in Phase 5)
# ============================================================
INTENT_PARSER_SYSTEM = """\
You are the intent parser for a Thai/English bilingual TPM (Total Productive Maintenance)
AI assistant. Extract structured intent from a user's request.

Output fields:
  - action: one of [lookup, analyze, report, calc, plan, edit, vision, other]
  - subject: the equipment/document/standard being asked about (NOT the
             word "prompt" or "message" - those are meta-talk, not the subject)
  - scope: WHAT the user wants done with the subject (definition, comparison,
           translation, latest data, ...). Include language preference here.
  - constraints: dict (time range, format, language: "th"|"en", etc.)
  - confidence: 0.0-1.0 - prefer 0.5-0.7 if request is vague
  - missing: list of slot names still empty
  - alternatives: up to 3 other interpretations if ambiguous

CRITICAL distinctions:
  1. "ตอบเป็นภาษาไทย" / "in Thai" / "แปลเป็น..." are LANGUAGE PREFERENCES
     -> add {"language": "th"} to constraints. Do NOT change subject to "prompt".
  2. "what is ASTM A106 ตอบเป็นไทย" -> subject="ASTM A106", scope="definition",
     constraints={"language": "th"}.
  3. Words like "prompt", "the message", "what I asked" are META references
     to the conversation, NOT the subject. Subject must be the engineering thing.
  4. If user mentions a number or code (e.g. "SKF 6205", "B-2"), that's likely
     subject - keep it verbatim.

Lane signals (set true if applicable):
  - is_definition: user asks "what is X" / "นิยาม" / "คืออะไร"
  - is_standard_reference: asks about ISO/ASME/JIS/มอก./ASTM standard
  - needs_grounding: needs cited evidence / source pointers
  - feed_to_llm: result will be summarized for further LLM use
  - is_recent: needs recent/current data ("ล่าสุด", "today", "2026")
  - is_research: research-style multi-step query
  - is_simple_lookup: direct fact lookup

Output VALID JSON ONLY. No prose around it.
"""

INTENT_PARSER_SCHEMA = {
    "type": "object",
    "required": ["action", "subject", "scope", "confidence", "missing", "alternatives"],
    "properties": {
        "action": {"type": "string"},
        "subject": {"type": "string"},
        "scope": {"type": "string"},
        "constraints": {"type": "object"},
        "confidence": {"type": "number"},
        "missing": {"type": "array", "items": {"type": "string"}},
        "alternatives": {"type": "array", "items": {"type": "string"}},
        "is_definition": {"type": "boolean"},
        "is_standard_reference": {"type": "boolean"},
        "needs_grounding": {"type": "boolean"},
        "feed_to_llm": {"type": "boolean"},
        "is_recent": {"type": "boolean"},
        "is_research": {"type": "boolean"},
        "is_simple_lookup": {"type": "boolean"},
    },
}

CLARIFY_QUESTION_SYSTEM = """\
You are the clarification dialog generator for a TPM AI assistant. Given:
  - the user's request history
  - the AI's current best interpretation
  - which slots are still missing

Generate ONE concise clarification question in the user's language (auto-detect from
their input - usually Thai). Include up to 3 specific options labeled A/B/C and
an "อื่นๆ" (other) escape hatch. Keep options short (one line each).

Output JSON:
{
  "question": "<the question text in Thai/English matching user>",
  "options": ["A) ...", "B) ...", "C) ...", "อื่นๆ - พิมพ์อธิบายเพิ่ม"]
}
"""

CLARIFY_QUESTION_SCHEMA = {
    "type": "object",
    "required": ["question", "options"],
    "properties": {
        "question": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}},
    },
}


# ============================================================
# Frustration / skip detection
# ============================================================
_FRUSTRATED_PATTERNS = [
    r"อย่ามาถาม",
    r"ทำไปเลย",
    r"ไม่ต้องถาม",
    r"\bskip\s+clarify\b",
    r"\bgo ahead\b",
    r"\bjust do it\b",
    r"\bเอาแบบนี้แหละ\b",
    r"\bพอเเล้ว\b",
    r"\bพอแล้ว\b",
]


def user_wants_to_skip(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in _FRUSTRATED_PATTERNS)


# ============================================================
# Parse intent
# ============================================================
def parse_intent(model: str, history: list[str]) -> dict[str, Any]:
    """
    Send the conversation history to the LLM and get back a parsed intent dict.
    Returns the raw dict (not Intent object) so caller can decide what to do.
    """
    user_block = "\n---\n".join(f"User turn {i+1}: {t}" for i, t in enumerate(history))
    messages = [
        {"role": "system", "content": INTENT_PARSER_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    return chat_json(model, messages, json_schema=INTENT_PARSER_SCHEMA, temperature=0.1)


# ============================================================
# Generate clarification question
# ============================================================
def generate_clarification_question(
    model: str,
    history: list[str],
    intent_dict: dict[str, Any],
) -> dict[str, Any]:
    user_block = "\n---\n".join(f"User turn {i+1}: {t}" for i, t in enumerate(history))
    interp_block = (
        f"Current interpretation:\n"
        f"  action: {intent_dict.get('action')}\n"
        f"  subject: {intent_dict.get('subject')}\n"
        f"  scope: {intent_dict.get('scope')}\n"
        f"  confidence: {intent_dict.get('confidence')}\n"
        f"  missing slots: {intent_dict.get('missing', [])}\n"
        f"  alternatives: {intent_dict.get('alternatives', [])}\n"
    )
    messages = [
        {"role": "system", "content": CLARIFY_QUESTION_SYSTEM},
        {"role": "user", "content": user_block + "\n\n" + interp_block},
    ]
    return chat_json(model, messages, json_schema=CLARIFY_QUESTION_SCHEMA, temperature=0.4)


# ============================================================
# Build Intent from raw dict
# ============================================================
def to_intent(intent_dict: dict[str, Any], history: list[str]) -> Intent:
    return Intent(
        action=intent_dict.get("action", "") or "",
        subject=intent_dict.get("subject", "") or "",
        scope=intent_dict.get("scope", "") or "",
        constraints=intent_dict.get("constraints", {}) or {},
        confidence=float(intent_dict.get("confidence", 0.0) or 0.0),
        history=list(history),
        is_definition=bool(intent_dict.get("is_definition", False)),
        is_standard_reference=bool(intent_dict.get("is_standard_reference", False)),
        needs_grounding=bool(intent_dict.get("needs_grounding", False)),
        feed_to_llm=bool(intent_dict.get("feed_to_llm", False)),
        is_recent=bool(intent_dict.get("is_recent", False)),
        is_research=bool(intent_dict.get("is_research", False)),
        is_simple_lookup=bool(intent_dict.get("is_simple_lookup", False)),
    )
