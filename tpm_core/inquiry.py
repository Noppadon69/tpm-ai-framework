"""
tpm_core.inquiry - Inquiry-First Pattern (Section 8)
ref: MASTER_PLAN_v6.md Section 8

Detect when an intent points to USER-SPECIFIC information (a specific machine,
internal file, person, internal location) and ask the user before searching the
web. Saves time, avoids egress for things only the user knows, and produces
better-grounded answers.

Design notes for v1:
  - Deterministic (pattern + intent slot based). NO LLM call inside this node.
    Keeps it ~free in tokens and instant in latency.
  - Skip rules from Section 8.6 implemented up-front so we don't ask twice
    when the answer is obviously general-knowledge.
  - Wiki integration deferred (Phase 1 Day 1-3 still blocked on real Toshiba
    data). For now: detect -> ask -> route.
  - Memory integration (Section 8.5) deferred until ChromaDB user_memory
    collection is wired in Phase 2.5. Answers are still recorded on the
    TPMState for replay / Night Cycle use.

Routes (stored on state.inquiry_route):
  user_answered     - user supplied the answer directly; use it
  location_provided - user pointed at a file/path; downstream reads it
  search            - user said "don't know"; fall through to L3
  skipped           - skip rule fired; no question asked
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

from tpm_core.state import Intent

log = logging.getLogger(__name__)

# ============================================================
# Skip rules (Section 8.6)
# ============================================================

# Emergency keywords - skip inquiry, use best-effort + flag (Section 8.6)
_EMERGENCY_PATTERNS = [
    r"ด่วน",
    r"ฉุกเฉิน",
    r"ไหม้",
    r"ระเบิด",
    r"\bemergency\b",
    r"\burgent\b",
    r"\basap\b",
]


def is_emergency(user_request: str) -> bool:
    text = user_request.lower()
    return any(re.search(p, text) for p in _EMERGENCY_PATTERNS)


def is_night_cycle() -> bool:
    """Night Cycle replay sets TPM_NIGHT_MODE=1 - don't wake the user."""
    return os.environ.get("TPM_NIGHT_MODE", "").strip() in {"1", "true", "yes"}


# ============================================================
# User-specific detection (Section 8.3)
# ============================================================

# Patterns that almost always mean "company/user-specific"
_USER_SPECIFIC_PATTERNS = [
    # Thai
    r"เครื่องของเรา",
    r"ของเรา",
    r"ของบริษัท",
    r"ในโรงงาน",
    r"ที่โรงงาน",
    r"ใครรับผิดชอบ",
    r"ของใคร",
    r"ห้องไหน",
    r"ไลน์ไหน",
    r"แผนกไหน",
    # English
    r"\binternal\b",
    r"\bin[- ]house\b",
    r"\bour (?:machine|line|plant|factory|team)\b",
    r"\bwho (?:owns|maintains|is responsible)\b",
    r"\bcompany[- ]specific\b",
]

# Machine-tag heuristic: short word + (- or #) + digit
# Captures: "B-2", "M-101", "L-23A", "PUMP-04", "Boiler #2", "Pump#3"
# Requires the dash/hash to avoid matching "TRIZ 35" or "ISO 9001" (which are
# standards, not internal tags).
_MACHINE_TAG_RE = re.compile(
    r"\b[A-Za-z][A-Za-z]{0,8}\s?[-#]\s?\d{1,4}[A-Z]?\b"
)

# Known equipment vendors that strongly imply Toshiba internal context
# (matches even without explicit "our" wording)
_INTERNAL_VENDOR_TOKENS = {
    "makino", "shibaura", "sodick", "fanuc",
}


@dataclass(frozen=True)
class InquiryDecision:
    """Output of should_inquire()."""
    needed: bool
    reason: str
    # When needed=True, these slots tell the question generator what to ask about.
    target_phrase: str = ""

    @property
    def skip(self) -> bool:
        return not self.needed


def is_user_specific(intent: Intent, user_request: str) -> bool:
    """
    True if the request mentions a user-specific entity (a machine code,
    internal vendor, "our X", "who maintains", etc).
    """
    haystack = f"{user_request} {intent.subject} {intent.scope}".lower()

    # Pattern check
    for p in _USER_SPECIFIC_PATTERNS:
        if re.search(p, haystack, flags=re.IGNORECASE):
            return True

    # Machine-tag-like token
    if _MACHINE_TAG_RE.search(f"{user_request} {intent.subject}"):
        return True

    # Internal vendor token
    if any(tok in haystack for tok in _INTERNAL_VENDOR_TOKENS):
        return True

    return False


def should_inquire(intent: Intent, user_request: str) -> InquiryDecision:
    """
    Section 8.2 decision tree + Section 8.6 skip rules.
    Returns an InquiryDecision; caller asks the user only when needed=True.
    """
    # --- Skip rule: emergency mode ---
    if is_emergency(user_request):
        return InquiryDecision(False, "emergency_mode")

    # --- Skip rule: night cycle ---
    if is_night_cycle():
        return InquiryDecision(False, "night_cycle")

    # --- Skip rule: clearly general knowledge ---
    # is_definition and is_standard_reference come from the intent parser.
    # If either is true we already know the request is about a public concept
    # (TRIZ principle, ASME code, FMEA definition, etc.).
    if intent.is_definition or intent.is_standard_reference:
        return InquiryDecision(False, "general_knowledge")

    # --- Skip rule: user already provided ---
    # If the latest clarification turn was a substantive answer (>20 chars)
    # we treat that as the user-provided fact.
    if intent.history and len(intent.history) >= 2:
        latest = intent.history[-1].strip()
        if len(latest) > 20 and "?" not in latest:
            # Heuristic: looks like an answer, not a question
            pass  # fall through to user-specific check; the check decides

    # --- Main check ---
    if is_user_specific(intent, user_request):
        target = intent.subject or _extract_first_tag(user_request) or user_request[:60]
        return InquiryDecision(True, "user_specific", target_phrase=target)

    # Default: skip
    return InquiryDecision(False, "not_user_specific")


def _extract_first_tag(text: str) -> Optional[str]:
    m = _MACHINE_TAG_RE.search(text)
    return m.group(0) if m else None


# ============================================================
# Question generation (Section 8.4 dialog)
# ============================================================

def build_inquiry_prompt(intent: Intent, decision: InquiryDecision) -> dict:
    """
    Build the inquiry question + 3 options (Section 8.4 dialog template).
    Returns {"question": str, "options": list[str]}.

    Language: Thai if intent.constraints.language == 'th' or if subject has
    Thai chars; English otherwise.
    """
    target = decision.target_phrase or intent.subject or "this"
    lang = (intent.constraints or {}).get("language", "")
    if not lang:
        lang = "th" if _has_thai(target + intent.scope) else "en"

    if lang == "th":
        question = (
            f"ผมต้องข้อมูลของ \"{target}\" — ก่อนค้น web "
            f"ขอถามคุณก่อน: คุณรู้รายละเอียดที่ผมต้องไหมครับ?"
        )
        options = [
            "A) รู้ — พิมพ์คำตอบให้ผมเลย",
            "B) ดูที่ไฟล์/path ... (ระบุ)",
            "C) ผมไม่รู้ — ค้น web ให้",
        ]
    else:
        question = (
            f"I need info about \"{target}\" — before I search the web, "
            f"do you have the answer?"
        )
        options = [
            "A) Yes - I'll tell you",
            "B) Check this file/path ... (specify)",
            "C) I don't know - search web",
        ]
    return {"question": question, "options": options}


def _has_thai(s: str) -> bool:
    return any("฀" <= c <= "๿" for c in s)


# ============================================================
# Answer parsing
# ============================================================

# Tokens that mean "I don't know - go search"
_DONT_KNOW_TOKENS = {
    "c", "c)", "ค้น", "ไม่รู้", "search", "i don't know", "ไม่ทราบ",
    "don't know", "dunno", "no idea",
}

# Tokens that mean "I'll tell you directly"
_YES_KNOW_TOKENS = {
    "a", "a)", "ครับ", "yes", "รู้",
}

# Hint that the user is pointing at a path/url instead of answering
_LOCATION_HINT_RE = re.compile(
    r"(?:[a-zA-Z]:[\\/]|/[a-zA-Z]|https?://|\\\\|\.(?:xlsx|csv|md|pdf|docx|txt|json|yaml)\b)",
    flags=re.IGNORECASE,
)


@dataclass
class InquiryAnswer:
    route: str          # 'user_answered' | 'location_provided' | 'search'
    payload: str        # the answer text, the location path, or '' for search
    raw: str            # original user input


def parse_inquiry_answer(answer: str) -> InquiryAnswer:
    """Classify a user reply to an inquiry question into one of 3 routes."""
    raw = answer or ""
    a = raw.strip()
    a_low = a.lower()

    # 1. C) / I don't know -> search
    if a_low in _DONT_KNOW_TOKENS or a_low.startswith(("c)", "c ", "c-")):
        return InquiryAnswer("search", "", raw)

    # 2. B) / path / URL -> location
    if a_low.startswith(("b)", "b ", "b-")) or _LOCATION_HINT_RE.search(a):
        # Strip the leading "B) " if present
        payload = re.sub(r"^[bB][\)\.\s-]+\s*", "", a).strip()
        return InquiryAnswer("location_provided", payload or a, raw)

    # 3. A) / yes / direct answer -> user_answered
    if a_low.startswith(("a)", "a ", "a-")) or a_low in _YES_KNOW_TOKENS:
        # If they only typed "A" with no content, treat as needing a follow-up.
        # The orchestrator's node handles that case by asking again. Here we
        # store whatever payload we got.
        payload = re.sub(r"^[aA][\)\.\s-]+\s*", "", a).strip()
        return InquiryAnswer("user_answered", payload, raw)

    # 4. Free-text reply that doesn't match A/B/C - treat as direct answer
    if len(a) >= 3:
        return InquiryAnswer("user_answered", a, raw)

    # 5. Empty / too short - fall through to search
    return InquiryAnswer("search", "", raw)
