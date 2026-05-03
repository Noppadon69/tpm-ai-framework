"""
tpm_night.discrepancy - compare original session vs replay
ref: MASTER_PLAN_v5.md § 15.3

What we compare:
    1. final_phase            - did it succeed?
    2. provider used (search) - did router pick the same lane?
    3. n_results              - similar count?
    4. action / subject       - intent stable?
    5. output_files count     - did worker produce same artifacts?
    6. duration               - latency drift?

Output: list of Discrepancy with severity + diagnosis hint.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from tpm_night.session_store import SessionRecord

log = logging.getLogger(__name__)


@dataclass
class Discrepancy:
    field: str
    severity: str        # "info" | "warn" | "error"
    original: Any
    replay: Any
    hint: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "severity": self.severity,
            "original": self.original,
            "replay": self.replay,
            "hint": self.hint,
        }


# ============================================================
# Compare
# ============================================================
def compare_runs(
    original: SessionRecord,
    replay_final: Any,
    *,
    duration_drift_pct: float = 0.5,
) -> list[Discrepancy]:
    """Return list of Discrepancy items, severity-ordered (errors first)."""
    out: list[Discrepancy] = []

    if replay_final is None:
        out.append(Discrepancy(
            field="replay_status",
            severity="error",
            original="completed",
            replay="None (replay failed)",
            hint="replay invoke threw - investigate model/timeout",
        ))
        return out

    # ---- 1. final phase ----
    rep_phase = replay_final.phase.value if hasattr(replay_final, "phase") else replay_final.get("phase")
    if rep_phase != original.final_phase:
        out.append(Discrepancy(
            field="final_phase",
            severity="error" if (original.final_phase == "done") else "warn",
            original=original.final_phase,
            replay=rep_phase,
            hint=(
                "replay diverged: prompt instability or model nondeterminism"
                if original.final_phase == "done" else
                "replay improved on original - consider promoting fix"
            ),
        ))

    # ---- 2. intent action stability ----
    orig_action = (original.intent or {}).get("action", "")
    rep_intent = getattr(replay_final, "intent", None)
    rep_action = rep_intent.action if rep_intent else ""
    if orig_action and rep_action and orig_action != rep_action:
        out.append(Discrepancy(
            field="intent.action",
            severity="warn",
            original=orig_action,
            replay=rep_action,
            hint="intent parser unstable - lower temperature or refine system prompt",
        ))

    # ---- 3. search provider lane ----
    orig_provider = (original.final_output or {}).get("search", {}).get("provider")
    rep_search = (
        (replay_final.final_output or {}).get("search", {})
        if hasattr(replay_final, "final_output") else {}
    )
    rep_provider = rep_search.get("provider")
    if orig_provider and rep_provider and orig_provider != rep_provider:
        out.append(Discrepancy(
            field="search.provider",
            severity="info",
            original=orig_provider,
            replay=rep_provider,
            hint="lane changed - check if Intent flags were re-extracted differently",
        ))

    # ---- 4. n_results sanity ----
    orig_n = (original.final_output or {}).get("search", {}).get("n_results", 0)
    rep_n = rep_search.get("n_results", 0)
    if orig_n and rep_n:
        delta = abs(orig_n - rep_n) / max(orig_n, rep_n)
        if delta > 0.5:
            out.append(Discrepancy(
                field="search.n_results",
                severity="info",
                original=orig_n,
                replay=rep_n,
                hint="result count drift - possibly cache freshness or upstream change",
            ))

    # ---- 5. worker output_files count ----
    orig_files = (original.final_output or {}).get("output_files", []) or []
    rep_files = []
    if hasattr(replay_final, "final_output"):
        rep_files = (replay_final.final_output or {}).get("output_files", []) or []
    if len(orig_files) != len(rep_files):
        out.append(Discrepancy(
            field="worker.output_files",
            severity="warn",
            original=len(orig_files),
            replay=len(rep_files),
            hint="worker produced different number of artifacts",
        ))

    # ---- 6. duration drift ----
    orig_dur = original.duration_ms or 0
    rep_dur = 0
    if hasattr(replay_final, "handoff_log"):
        # Approximate replay duration from handoff metadata if present
        rep_dur = sum(
            getattr(p, "payload", {}).get("latency_ms", 0)
            for p in replay_final.handoff_log
        )
    if orig_dur > 0 and rep_dur > 0:
        drift = abs(rep_dur - orig_dur) / orig_dur
        if drift > duration_drift_pct:
            out.append(Discrepancy(
                field="duration_ms",
                severity="info",
                original=orig_dur,
                replay=rep_dur,
                hint=f"replay {drift*100:.0f}% slower/faster - check thermal or cold-start",
            ))

    # Sort: errors first, then warn, then info
    sev_order = {"error": 0, "warn": 1, "info": 2}
    out.sort(key=lambda d: sev_order.get(d.severity, 3))
    return out


def is_clean(discrepancies: list[Discrepancy]) -> bool:
    """No errors and no warnings = clean replay."""
    return not any(d.severity in ("error", "warn") for d in discrepancies)
