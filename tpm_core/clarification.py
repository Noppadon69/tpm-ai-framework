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

    Bug #6 defense (two layers):
      1) Mitigation (commit bbf100d): temperature=0.05 + seed=42 + timeout=60
         avoids the Ollama grammar-stuck-sampling hang AND fails fast if it
         happens anyway (vs 180s default). Sufficient on Ollama >= 0.23 for
         the prompts we've seen.
      2) Permanent fallback (this commit 2026-05-13): on ANY LLM failure
         (timeout, network drop, JSON parse error after retries), fall back
         to a deterministic rule-based classifier that mirrors the
         disambiguation rules in INTENT_PARSER_SYSTEM. Confidence <= 0.55
         so the orchestrator's clarification loop kicks in - same recovery
         path it uses for any other low-confidence interpretation. Net
         result: parse_intent NEVER crashes even if Ollama spins forever.
    """
    user_block = "\n---\n".join(f"User turn {i+1}: {t}" for i, t in enumerate(history))
    messages = [
        {"role": "system", "content": INTENT_PARSER_SYSTEM},
        {"role": "user", "content": user_block},
    ]
    try:
        return chat_json(
            model,
            messages,
            json_schema=INTENT_PARSER_SCHEMA,
            temperature=0.05,
            seed=42,
            timeout=60.0,
        )
    except Exception as e:  # noqa: BLE001
        log.warning(
            "parse_intent: LLM call failed (%s: %s) - using deterministic "
            "rule-based fallback (Bug #6 permanent defense)",
            type(e).__name__, str(e)[:120],
        )
        return _fallback_intent_from_rules(history)


# ============================================================
# Bug #6 permanent fallback - deterministic rule-based intent
# ============================================================
# Disambiguation patterns (first match wins) mirror the system-prompt rules.
# Keep ASCII keywords lowercase; Thai keywords as-is.
_RULES_LOOKUP_DEF = (
    " vs ", "ต่างกัน", "compare", "what is", "คืออะไร", "นิยาม",
    "อธิบาย", "เป็นอะไร", " versus ", "หมายถึง",
)
_RULES_EXCEL    = ("excel", ".xlsx", "spreadsheet", "ออกเป็น excel", "เป็น excel")
_RULES_REPORT   = ("เขียนรายงาน", "write a report", "report ของ", "report on", "draft report")
_RULES_VISION   = ("รูป", "ภาพ", " image ", " photo ", "picture", "เห็นในรูป", "vlm")
_RULES_CALC     = ("คำนวณ", "calculate", "คิด", "ผลคูณ", "ผลรวม", "compute ", "stress", "force")
_RULES_ANALYZE  = ("pareto", "trend", "downtime", "วิเคราะห์", "histogram", "data analysis")
_RULES_PLAN     = ("schedule", "ตารางเวลา", "pm plan", "action items", "วางแผน")
_RULES_EDIT     = ("แก้ไข", "modify", "update file", "เปลี่ยน")


def _fallback_intent_from_rules(history: list[str]) -> dict[str, Any]:
    """
    Rule-based intent dict matching INTENT_PARSER_SCHEMA. Used when the LLM
    parse_intent path fails. Order mirrors the system-prompt disambiguation
    rules so behavior is consistent. Confidence is capped at 0.55 so the
    orchestrator's clarification loop refines it.
    """
    text = " ".join(history).lower() if history else ""
    raw_text = " ".join(history) if history else ""

    if any(kw in text for kw in _RULES_LOOKUP_DEF):
        return _build_fallback("lookup", raw_text, confidence=0.55,
                               is_definition=True, is_simple_lookup=True)
    if any(kw in text for kw in _RULES_EXCEL):
        return _build_fallback("excel", raw_text, confidence=0.50)
    if any(kw in text for kw in _RULES_REPORT):
        return _build_fallback("report", raw_text, confidence=0.50)
    if any(kw in text for kw in _RULES_VISION):
        return _build_fallback("vision", raw_text, confidence=0.50)
    if any(kw in text for kw in _RULES_CALC):
        return _build_fallback("calc", raw_text, confidence=0.50)
    if any(kw in text for kw in _RULES_ANALYZE):
        return _build_fallback("analyze", raw_text, confidence=0.50)
    if any(kw in text for kw in _RULES_PLAN):
        return _build_fallback("plan", raw_text, confidence=0.45)
    if any(kw in text for kw in _RULES_EDIT):
        return _build_fallback("edit", raw_text, confidence=0.45)
    # Rule 5 (system prompt): ambiguous query about equipment -> lookup (safest;
    # CONFIDENTIAL classification then runs egress check downstream).
    return _build_fallback("lookup", raw_text, confidence=0.35,
                           is_simple_lookup=True)


def _extract_fallback_subject(text: str) -> str:
    """
    Crude noun-phrase pick for fallback. Prefer ALL-CAPS engineering codes
    (SHIBAURA, MAKINO, M-101, ASTM, B-2) then alpha-numeric machine IDs,
    else longest non-stopword token.
    """
    if not text:
        return ""
    code_match = re.search(r"\b[A-Z][A-Z0-9\-]{2,}\b", text)
    if code_match:
        # strip trailing dashes (e.g. "MAKINO-a51nx" -> "MAKINO-" -> "MAKINO")
        return code_match.group(0).rstrip("-")
    tokens = [
        t.strip(".,!?:;\"'()") for t in text.split()
        if len(t.strip(".,!?:;\"'()")) >= 3 and not t.strip(".,!?:;\"'()").isnumeric()
    ]
    if not tokens:
        return ""
    stop = {"the", "and", "for", "what", "how", "this", "that", "with", "from",
            "ที่", "และ", "ของ", "หรือ", "ครับ", "ค่ะ"}
    candidates = [t for t in tokens if t.lower() not in stop]
    return max(candidates, key=len) if candidates else max(tokens, key=len)


def _build_fallback(
    action: str,
    raw_text: str,
    *,
    confidence: float,
    is_definition: bool = False,
    is_simple_lookup: bool = False,
) -> dict[str, Any]:
    """Common scaffold producing a schema-valid intent dict."""
    subject = _extract_fallback_subject(raw_text)
    return {
        "action": action,
        "subject": subject,
        "scope": "",
        "constraints": {},
        "confidence": confidence,
        "missing": [] if subject else ["subject"],
        "alternatives": [],
        "is_definition": is_definition,
        "is_standard_reference": False,
        "needs_grounding": False,
        "feed_to_llm": False,
        "is_recent": False,
        "is_research": False,
        "is_simple_lookup": is_simple_lookup,
        "_fallback": True,
    }


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
