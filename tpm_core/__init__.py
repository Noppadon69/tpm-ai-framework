"""
tpm_core - LangGraph orchestrator + clarification + state
ref: MASTER_PLAN_v5.md § 7, § 8, § 10

Public:
    from tpm_core import TPMState, run_orchestrator
"""
from tpm_core.state import (
    HandoffPacket,
    Intent,
    OrchestratorPhase,
    TPMState,
)
from tpm_core.orchestrator import run_orchestrator, build_graph

__all__ = [
    "TPMState",
    "HandoffPacket",
    "Intent",
    "OrchestratorPhase",
    "run_orchestrator",
    "build_graph",
]

__version__ = "0.1.0"
