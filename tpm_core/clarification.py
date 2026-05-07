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
Intent parser for a Thai/English TPM AI assistant. Extract structured intent.

Output fields:
  action (enum below); subject (the engineering thing); scope (what to do with it);
  constraints (dict: time_range, format, language "th"|"en", ...);
  confidence 0.0-1.0 (prefer 0.5-0.7 if vague);
  missing (empty slots); alternatives (<=3 other interpretations).

Actions:
  lookup  - definition/fact/standard or comparison
  analyze - chart/Pareto/trend on a SPECIFIC equipment + time range
  report  - explicit verb to author a PM/maintenance report
  excel   - user explicitly asks for .xlsx / Excel file output
  calc    - compute a number via formula
  plan    - schedule / PM plan / action items (no data crunch)
  edit    - modify an existing file
  vision  - read an image/photo/PDF
  other   - meta-talk / unclassified

Disambiguation (first match wins):
  1. "vs"/"ต่างกัน"/"compare"/"what is"/"คืออะไร"/"นิยาม"/"อธิบาย" -> action=lookup ALWAYS
  2. "Excel"/".xlsx"/"spreadsheet"/"ออกเป็น Excel" mention -> action=excel (BEFORE Pareto/trend rules)
  3. "เขียนรายงาน"/"write a report" + equipment + time range -> action=report
  4. "Pareto chart"/"downtime trend"/"data analysis" + equipment + time range -> action=analyze
  5. Ambiguous query about equipment without explicit verb -> action=lookup (safe; egress relies on this)

CRITICAL:
  - "ตอบเป็นภาษาไทย"/"in Thai"/"แปล..." are LANGUAGE PREFS: put {"language":"th"} in
    constraints. NEVER change subject to "prompt"/"message"/"what I asked".
  - Ex: "what is ASTM A106 ตอบเป็นไทย" -> subject="ASTM A106", language="th".
  - Codes like "SKF 6205", "B-2" -> keep verbatim as subject.

Lane signals (bool, set if applicable): is_definition, is_standard_reference,
needs_grounding, feed_to_llm, is_recent, is_research, is_simple_lookup.

Output VALID JSON ONLY. No prose.
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
    # temperature=0.05 + fixed seed -> near-deterministic intent classification.
    # Pure temp=0 + seed=42 + json_schema combined to deterministically produce
    # an empty response on certain prompts (Bug #6: "FMEA vs FTA ต่างกันยังไง").
    # Tiny temperature (0.05) breaks the degenerate sampling without breaking
    # day-to-day stability (action enum changes only on truly ambiguous prompts).
    # num_predict caps runtime; timeout=60 fails fast vs Ollama 180s default.
    return chat_json(
        model,
        messages,
        json_schema=INTENT_PARSER_SCHEMA,
        temperature=0.05,
        seed=42,
        timeout=60.0,
    )


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
