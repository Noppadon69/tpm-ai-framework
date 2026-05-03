"""
tpm_night - self-correction + replay + morning brief
ref: MASTER_PLAN_v5.md § 15 + 3-framework debugging insight (May 2026)

Public:
    from tpm_night import save_session, replay_session, run_night_cycle
"""
from tpm_night.session_store import (
    SessionRecord,
    list_sessions,
    load_session,
    save_session,
)
from tpm_night.replay import replay_session
from tpm_night.discrepancy import compare_runs, Discrepancy
from tpm_night.budget_audit import audit_prompts, audit_runtime
from tpm_night.morning_brief import render_brief, write_brief

__all__ = [
    "SessionRecord",
    "list_sessions",
    "load_session",
    "save_session",
    "replay_session",
    "compare_runs",
    "Discrepancy",
    "audit_prompts",
    "audit_runtime",
    "render_brief",
    "write_brief",
]

__version__ = "0.1.0"
