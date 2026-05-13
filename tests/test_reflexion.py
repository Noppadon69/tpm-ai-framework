"""
tests/test_reflexion.py - synthetic-data tests for Section 15.7 skeleton

Spec says actual rollout is deferred until internship Day 1 real failures.
These tests just verify the loop terminates correctly on synthetic
attempt/judge pairs.

Run:
    .venv/Scripts/python.exe tests/test_reflexion.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from tpm_reflexion import ReflexionConfig, run_reflexion  # noqa: E402
from tpm_reflexion.reflexion import default_reflect, format_outcome_for_brief  # noqa: E402

PASS = "[PASS]"
FAIL = "[FAIL]"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"{PASS} {name}")
    else:
        print(f"{FAIL} {name}  {detail}")
        _failures.append(name)


def t_immediate_success():
    """Round 1 hits threshold -> stop immediately."""
    out = run_reflexion(
        attempt_fn=lambda mem: "great answer",
        judge_fn=lambda txt, ctx: (0.95, []),
        config=ReflexionConfig(max_rounds=5, success_threshold=0.80),
    )
    check("immediate: success", out.success)
    check("immediate: 1 round", out.rounds_used == 1)
    check("immediate: reason threshold", out.reason == "threshold_reached")


def t_eventual_success():
    """Confidence climbs each round -> eventually passes threshold."""
    state = {"i": 0}

    def attempt(mem):
        state["i"] += 1
        return f"attempt {state['i']}, memory_len={len(mem)}"

    def judge(txt, ctx):
        # 0.3 -> 0.6 -> 0.85
        return (0.3 + 0.275 * (state["i"] - 1), ["missing X"])

    out = run_reflexion(
        attempt_fn=attempt, judge_fn=judge,
        config=ReflexionConfig(max_rounds=5, success_threshold=0.80),
    )
    check("eventual: success", out.success)
    check("eventual: ~3 rounds", out.rounds_used == 3)


def t_max_rounds_no_progress():
    """Constant low confidence -> stops at max_rounds OR no_improvement."""
    out = run_reflexion(
        attempt_fn=lambda mem: "stuck",
        judge_fn=lambda txt, ctx: (0.40, ["stuck note"]),
        config=ReflexionConfig(max_rounds=4, success_threshold=0.80, patience=2),
    )
    check("max-rnds: not successful", not out.success)
    check("max-rnds: short-circuited on no_improvement",
          out.reason == "no_improvement" and out.rounds_used <= 4)


def t_patience_kicks_in():
    """No improvement for >= patience rounds -> early stop."""
    confs = iter([0.30, 0.30, 0.30, 0.30])

    def judge(txt, ctx):
        try:
            return next(confs), ["repeat"]
        except StopIteration:
            return 0.0, []

    out = run_reflexion(
        attempt_fn=lambda mem: "x",
        judge_fn=judge,
        config=ReflexionConfig(max_rounds=10, success_threshold=0.80, patience=2),
    )
    check("patience: stops early", out.rounds_used < 10)
    check("patience: reason=no_improvement", out.reason == "no_improvement")


def t_reflection_grows_memory():
    """Memory list grows by one per non-successful round."""
    seen_mem_sizes: list[int] = []

    def attempt(mem):
        seen_mem_sizes.append(len(mem))
        return "x"

    out = run_reflexion(
        attempt_fn=attempt,
        judge_fn=lambda txt, ctx: (0.20, ["bad"]),
        config=ReflexionConfig(max_rounds=3, success_threshold=0.80, patience=10),
    )
    check("memory: 3 rounds happened", out.rounds_used == 3)
    check("memory: starts at 0",       seen_mem_sizes[0] == 0)
    check("memory: grows by 1 each round",
          seen_mem_sizes == [0, 1, 2])


def t_default_reflect_helpful():
    refl, fix = default_reflect("attempt text", ["missing pressure value"])
    check("reflect: text mentions judge note", "missing pressure value" in refl)
    check("reflect: produces a fix", bool(fix))


def t_default_reflect_no_notes():
    refl, fix = default_reflect("attempt text", [])
    check("reflect: handles empty notes", bool(refl))


def t_format_outcome_for_brief():
    out = run_reflexion(
        attempt_fn=lambda mem: "x",
        judge_fn=lambda txt, ctx: (0.50, ["note A", "note B"]),
        config=ReflexionConfig(max_rounds=2, success_threshold=0.80, patience=10),
    )
    md = format_outcome_for_brief(out, task_label="synthetic-test")
    check("brief: header present",   "Reflexion outcome" in md and "synthetic-test" in md)
    check("brief: lists rounds",      "Round 1" in md)
    check("brief: includes notes",    "note A" in md and "note B" in md)
    check("brief: deferred footer",   "Phase 1" in md and "30-day" in md)


def main() -> int:
    for fn in (
        t_immediate_success,
        t_eventual_success,
        t_max_rounds_no_progress,
        t_patience_kicks_in,
        t_reflection_grows_memory,
        t_default_reflect_helpful,
        t_default_reflect_no_notes,
        t_format_outcome_for_brief,
    ):
        print(f"\n--- {fn.__name__} ---")
        fn()
    print()
    if _failures:
        print(f"{FAIL} {len(_failures)} test(s) failed")
        return 1
    print(f"{PASS} all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
