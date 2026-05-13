"""
tpm_reflexion - Reflexion N-round (Section 15.7) skeleton
ref: MASTER_PLAN_v6.md Section 15.7

This is a SKELETON. The spec explicitly defers actual rollout until
internship Day 1 produces real failure data; building it now lets us
test the loop on synthetic cases and have the wiring ready when the
real failures land.

Phase 1 (= current scope): patches go to the morning brief ONLY.
Auto-promotion to prompt registry is Phase 2, requires > 80% user
approval rate over 30 days.
"""
from tpm_reflexion.reflexion import (
    RefletionRound,
    ReflexionConfig,
    ReflexionOutcome,
    run_reflexion,
)

__all__ = [
    "ReflexionConfig",
    "ReflexionOutcome",
    "RefletionRound",
    "run_reflexion",
]
