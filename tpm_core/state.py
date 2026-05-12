"""
tpm_core.state - LangGraph state + handoff schema
ref: MASTER_PLAN_v5.md § 10.2, § 10.3
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_session_id() -> str:
    return uuid.uuid4().hex[:12]


# ============================================================
# Phases - explicit state machine
# ============================================================
class OrchestratorPhase(str, Enum):
    INIT = "init"
    CLARIFY = "clarify"            # § 7
    INQUIRY = "inquiry"            # § 8
    PLAN = "plan"
    SEARCH = "search"
    WORK = "work"                  # worker subgraphs
    AUDIT = "audit"
    HUMAN_GATE = "human_gate"
    DONE = "done"
    FAILED = "failed"


# ============================================================
# Confirmed intent (output of clarification loop)
# ============================================================
class Intent(BaseModel):
    """The user's verified intent after clarification (§ 7.3)."""
    action: str = ""                       # e.g., "lookup", "report", "calc"
    subject: str = ""                      # e.g., "Boiler #2"
    scope: str = ""                        # e.g., "PM schedule + last 3 months"
    constraints: dict[str, Any] = Field(default_factory=dict)
    slots: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    user_override: bool = False
    history: list[str] = Field(default_factory=list)

    # Lane signals for L3 router (§ 6.4.0)
    is_definition: bool = False
    is_standard_reference: bool = False
    needs_grounding: bool = False
    has_output_schema: bool = False
    output_schema: Optional[dict[str, Any]] = None
    feed_to_llm: bool = False
    is_recent: bool = False
    is_research: bool = False
    is_simple_lookup: bool = False


# ============================================================
# Handoff packet (between LangGraph nodes - § 10.3)
# ============================================================
class HandoffPacket(BaseModel):
    stage: str
    success: bool = True
    confidence: float = 1.0
    reasoning: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    error_msg: str = ""
    confidence_breakdown: dict[str, str] = Field(default_factory=dict)
    # high_because / uncertain_about / would_increase_if


# ============================================================
# Master state (§ 10.2)
# ============================================================
class TPMState(BaseModel):
    # ---- session id ----
    session_id: str = Field(default_factory=_new_session_id)
    started_at: datetime = Field(default_factory=_utcnow)

    # ---- input ----
    user_request: str = ""

    # ---- clarification (§ 7) ----
    clarify_history: list[str] = Field(default_factory=list)
    clarify_iterations: int = 0
    clarify_max_iterations: int = 5
    clarify_min_confidence: float = 0.75   # well-formed queries score 0.7-0.85
    pending_question: Optional[str] = None
    pending_options: list[str] = Field(default_factory=list)

    # ---- confirmed intent ----
    intent: Optional[Intent] = None

    # ---- inquiry-first (§ 8) - filled when AI needs missing info ----
    inquiry_question: Optional[str] = None
    inquiry_answer: Optional[str] = None
    inquiry_route: Optional[str] = None      # user_answered | location_provided | search | skipped
    inquiry_skip_reason: Optional[str] = None
    inquiry_payload: Optional[str] = None    # the user's actual answer or location

    # ---- planning ----
    subtasks: list[dict[str, Any]] = Field(default_factory=list)
    plan_reasoning: str = ""

    # ---- recon (§ 10.1) ----
    recon_results: dict[str, Any] = Field(default_factory=dict)
    recon_quality: float = 0.0
    recon_complete: bool = False

    # ---- workers ----
    subtask_results: dict[str, Any] = Field(default_factory=dict)

    # ---- audit ----
    audit_passed: bool = False
    audit_failures: list[str] = Field(default_factory=list)
    retry_count: int = 0

    # ---- human gate ----
    human_approved: bool = False
    human_feedback: str = ""

    # ---- control ----
    phase: OrchestratorPhase = OrchestratorPhase.INIT
    final_output: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    handoff_log: list[HandoffPacket] = Field(default_factory=list)

    # ---- lineage (§ 10.2) ----
    model_name: str = "qwen3:8b-instruct-q4_K_M"
    prompt_hashes: dict[str, str] = Field(default_factory=dict)
    langgraph_trace_id: str = ""

    # ---- helpers ----
    def append_handoff(self, packet: HandoffPacket) -> None:
        self.handoff_log.append(packet)

    def is_terminal(self) -> bool:
        return self.phase in (OrchestratorPhase.DONE, OrchestratorPhase.FAILED)
