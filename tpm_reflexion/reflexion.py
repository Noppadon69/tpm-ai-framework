"""
tpm_reflexion.reflexion - N-round self-correction loop (Section 15.7)
ref: MASTER_PLAN_v6.md Section 15.7

Loop (pseudocode in Section 15.7.3):

    for round in 1..N:
        replay or attempt
        judge_verdict = auditor.judge(attempt)
        if judge_verdict.confidence >= threshold:
            return outcome(success, rounds_used=round)
        reflection = generate_reflection(attempt, judge_verdict)
        memory.append(reflection)
    return outcome(stuck, rounds_used=N, memory=memory)

This skeleton:
  - Plugs into the existing Auditor.judge() as the judge backend
    (Phase 3 Day 4 already built it).
  - Uses a callable `attempt_fn(memory) -> attempt_text` so callers
    can plug in either the real worker or a synthetic test.
  - Generates reflections via an LLM callable OR a synthetic
    "rule-of-thumb" generator (pre-internship, the LLM is overkill
    and slow; tests use the rule-of-thumb one).
  - Output: ReflexionOutcome that lists every round + final verdict.
    Production rollout writes this to the morning brief; auto-prompt
    update is DEFERRED until 30-day user-approval gate per Section 15.7.

Design quirks worth preserving for the spec:
  - "improvement" is tracked: if confidence does not strictly increase
    over the last `patience` rounds, stop early (saves judge cost).
  - Each reflection is stored verbatim; the loop never silently
    rewrites a previous reflection.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


# ============================================================
# Data structures
# ============================================================
@dataclass
class RefletionRound:
    """One round of attempt + verdict + reflection."""
    round_idx: int
    attempt_text: str
    judge_confidence: float
    judge_notes: list[str] = field(default_factory=list)
    reflection: str = ""
    # if applied: what change the LLM suggested for the next attempt
    proposed_fix: str = ""


@dataclass
class ReflexionConfig:
    max_rounds: int = 3
    success_threshold: float = 0.80     # judge confidence we accept as "done"
    patience: int = 2                   # stop if no improvement for N rounds
    # When False (default in production), this loop runs but the result is
    # ONLY written to the morning brief - prompts are NOT auto-updated.
    auto_apply_to_prompts: bool = False


@dataclass
class ReflexionOutcome:
    success: bool
    rounds: list[RefletionRound]
    final_confidence: float
    reason: str                        # 'threshold_reached' | 'no_improvement' | 'max_rounds'

    @property
    def rounds_used(self) -> int:
        return len(self.rounds)


# ============================================================
# Type aliases for plug-in callables
# ============================================================
AttemptFn = Callable[[list[str]], str]
# Takes the list of past reflections, returns the next attempt text.

JudgeFn = Callable[[str, dict[str, Any]], tuple[float, list[str]]]
# Takes (attempt_text, ctx) -> (confidence_0_to_1, notes)
# This wraps Auditor.judge() in the production path.

ReflectFn = Callable[[str, list[str]], tuple[str, str]]
# Takes (attempt_text, judge_notes) -> (reflection_text, proposed_fix)


# ============================================================
# Default reflection generator (no LLM)
# Pre-internship the LLM-driven version is overkill - we synthesize a
# reflection from the judge's findings. Used by unit tests + early soak.
# ============================================================
def default_reflect(attempt_text: str, judge_notes: list[str]) -> tuple[str, str]:
    if not judge_notes:
        return ("attempt looked fine but did not meet threshold; "
                "consider adding more grounding context.", "expand grounding")
    head = judge_notes[0]
    reflection = (
        f"Judge flagged: {head!r}. "
        f"Hypothesis: the attempt is missing the specific fact or constraint "
        f"called out by the judge."
    )
    # Extract the most actionable noun phrase from the head finding
    fix = f"address: {head}"
    return reflection, fix


# ============================================================
# Auditor-backed judge wrapper (production path)
# ============================================================
def make_auditor_judge() -> JudgeFn:
    """
    Build a JudgeFn that delegates to the existing Auditor.judge().
    This is the Section 15.7 re-scope - Auditor IS the judge backend.
    """
    from tpm_workers.auditor import Auditor

    auditor = Auditor()

    def judge(attempt_text: str, ctx: dict[str, Any]) -> tuple[float, list[str]]:
        verdict = auditor.judge(attempt_text, task_context=ctx)
        return float(verdict.confidence), list(verdict.notes)

    return judge


# ============================================================
# Loop
# ============================================================
def run_reflexion(
    attempt_fn: AttemptFn,
    judge_fn: JudgeFn,
    *,
    task_context: Optional[dict[str, Any]] = None,
    reflect_fn: ReflectFn = default_reflect,
    config: Optional[ReflexionConfig] = None,
) -> ReflexionOutcome:
    """
    Run an N-round Reflexion loop.

    Returns ReflexionOutcome even when not successful - the morning brief
    consumes the structure either way.
    """
    cfg = config or ReflexionConfig()
    ctx = task_context or {}
    memory: list[str] = []
    rounds: list[RefletionRound] = []
    last_conf: Optional[float] = None
    stagnant_rounds = 0

    for i in range(1, cfg.max_rounds + 1):
        attempt = attempt_fn(memory)
        conf, notes = judge_fn(attempt, ctx)
        round_rec = RefletionRound(
            round_idx=i,
            attempt_text=attempt,
            judge_confidence=conf,
            judge_notes=list(notes),
        )

        log.info("reflexion round=%d conf=%.2f notes=%d", i, conf, len(notes))

        if conf >= cfg.success_threshold:
            rounds.append(round_rec)
            return ReflexionOutcome(
                success=True, rounds=rounds, final_confidence=conf,
                reason="threshold_reached",
            )

        # Generate reflection + fix idea before next round
        reflection, fix = reflect_fn(attempt, notes)
        round_rec.reflection = reflection
        round_rec.proposed_fix = fix
        memory.append(reflection)
        rounds.append(round_rec)

        # Early-stop on no improvement (patience)
        if last_conf is not None and conf <= last_conf + 1e-4:
            stagnant_rounds += 1
            if stagnant_rounds >= cfg.patience:
                return ReflexionOutcome(
                    success=False, rounds=rounds, final_confidence=conf,
                    reason="no_improvement",
                )
        else:
            stagnant_rounds = 0
        last_conf = conf

    # Ran out of rounds
    final_conf = rounds[-1].judge_confidence if rounds else 0.0
    return ReflexionOutcome(
        success=False, rounds=rounds, final_confidence=final_conf,
        reason="max_rounds",
    )


# ============================================================
# Morning-brief formatter (Section 15.7 Phase 1 output)
# ============================================================
def format_outcome_for_brief(outcome: ReflexionOutcome, task_label: str = "") -> str:
    """Render outcome as a markdown block to embed in the Night Cycle morning brief."""
    head = f"## Reflexion outcome - {task_label}" if task_label else "## Reflexion outcome"
    lines = [
        head,
        f"- success: {outcome.success}",
        f"- rounds used: {outcome.rounds_used}",
        f"- final confidence: {outcome.final_confidence:.2f}",
        f"- stop reason: {outcome.reason}",
        "",
    ]
    for r in outcome.rounds:
        lines.append(f"### Round {r.round_idx}  (judge conf={r.judge_confidence:.2f})")
        if r.judge_notes:
            lines.append("**Judge notes:**")
            for n in r.judge_notes:
                lines.append(f"  - {n}")
        if r.reflection:
            lines.append(f"**Reflection:** {r.reflection}")
        if r.proposed_fix:
            lines.append(f"**Proposed fix:** `{r.proposed_fix}`")
        lines.append("")
    lines.append(
        "_Phase 1 of Section 15.7: this output goes to the morning brief only. "
        "Auto-prompt update is gated on 30-day user-approval > 80%._"
    )
    return "\n".join(lines)
