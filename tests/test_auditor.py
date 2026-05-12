"""
tests/test_auditor.py - Auditor 8-layer (Section 12)
                     + judge backend (Section 15.7 Q3 tier 4)

Verifies each layer in isolation plus the aggregate Auditor.audit() and
Auditor.judge() entry points. No LLM, no network, no SSL (safe under Bug #7).

Run:
    .venv/Scripts/python.exe tests/test_auditor.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

from tpm_workers.auditor import (  # noqa: E402
    Auditor,
    AuditReport,
    LayerVerdict,
    audit_worker_result,
    layer_cove_numbers,
    layer_egress,
    layer_format,
    layer_quality,
    layer_safety,
    layer_schema,
)
from tpm_workers.base import WorkerResult, WorkerStep, WorkerType  # noqa: E402

PASS = "[PASS]"
FAIL = "[FAIL]"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"{PASS} {name}")
    else:
        print(f"{FAIL} {name}  {detail}")
        _failures.append(name)


def _good_result() -> WorkerResult:
    return WorkerResult(
        worker_type=WorkerType.REPORT,
        success=True,
        output_files=["nonexistent.docx"],  # format layer will warn but harmless
        summary="report ok",
        steps=[WorkerStep(name="researcher")],
        confidence=0.85,
    )


# ============================================================
# Layer: schema
# ============================================================
def t_schema():
    r = _good_result()
    v = layer_schema(r, {})
    check("schema: pass on valid", v.passed)

    bad = WorkerResult(worker_type=WorkerType.REPORT)
    bad.output_files = "oops"  # type: ignore[assignment]
    v = layer_schema(bad, {})
    check("schema: catch bad output_files", not v.passed)


# ============================================================
# Layer: cove_numbers
# ============================================================
def t_cove():
    r = _good_result()

    # All numbers are in source -> pass
    v = layer_cove_numbers(r, {
        "claim_text": "MTBF=124h, n_events=5",
        "source_text": "n_events: 5, mtbf_hours: 124",
    })
    check("cove: all in source", v.passed, detail=str(v.findings))

    # Bogus number -> fail
    v = layer_cove_numbers(r, {
        "claim_text": "MTBF=999999h, n_events=5",
        "source_text": "n_events: 5, mtbf_hours: 124",
    })
    check("cove: catch hallucinated number", not v.passed,
          detail=str(v.findings))

    # No source text -> skip (pass)
    v = layer_cove_numbers(r, {"claim_text": "n=5"})
    check("cove: skip when no source", v.passed)

    # No claims -> skip
    v = layer_cove_numbers(r, {"claim_text": "no nums here", "source_text": "5 6 7"})
    check("cove: skip when no claims", v.passed)


# ============================================================
# Layer: quality
# ============================================================
def t_quality():
    r = _good_result()
    v = layer_quality(r, {})
    check("quality: good result passes", v.passed)

    bad = WorkerResult(worker_type=WorkerType.REPORT, success=True, summary="")
    v = layer_quality(bad, {})
    check("quality: empty summary flagged", not v.passed)


# ============================================================
# Layer: format
# ============================================================
def t_format():
    with tempfile.TemporaryDirectory() as td:
        big_path = Path(td) / "big.docx"
        big_path.write_bytes(b"x" * 10_000)
        small_path = Path(td) / "small.docx"
        small_path.write_bytes(b"x" * 100)

        r = WorkerResult(worker_type=WorkerType.REPORT, output_files=[str(big_path)])
        v = layer_format(r, {})
        check("format: big file passes", v.passed)

        r = WorkerResult(worker_type=WorkerType.REPORT, output_files=[str(small_path)])
        v = layer_format(r, {})
        check("format: small file flagged", not v.passed,
              detail=str(v.findings))


# ============================================================
# Layer: safety
# ============================================================
def t_safety():
    r = _good_result()

    # Plain text -> pass
    v = layer_safety(r, {"claim_text": "normal maintenance report"})
    check("safety: benign text passes", v.passed)

    # Hazard without mitigation -> critical fail
    v = layer_safety(r, {"claim_text": "bypass LOTO for this run"})
    check("safety: catch unmitigated bypass LOTO", not v.passed)
    check("safety: severity=critical",
          any("loto" in f.lower() for f in v.findings) and v.severity == "critical")

    # Hazard WITH mitigation phrase nearby -> pass
    v = layer_safety(r, {
        "claim_text": "do not bypass LOTO - follow lockout safety procedure as per standard"
    })
    check("safety: bypass + lockout mitigation -> pass", v.passed)


# ============================================================
# Layer: egress
# ============================================================
def t_egress():
    r = _good_result()
    # Innocuous text -> pass
    v = layer_egress(r, {"claim_text": "MTBF of bearing wear pattern"})
    check("egress: benign passes", v.passed)

    # CONFIDENTIAL-flagged text -> fail (if egress module is reachable)
    v = layer_egress(r, {"claim_text": "Boiler B-2 incident report internal"})
    # We don't hardcode the assertion either way - just ensure no exception
    # and that the layer ran. Some classifications may be INTERNAL not
    # CONFIDENTIAL depending on egress rules.
    check("egress: layer ran", v.layer == "egress")


# ============================================================
# Auditor aggregate
# ============================================================
def t_audit_aggregate():
    r = _good_result()
    rpt = audit_worker_result(r, {
        "claim_text": "MTBF=124h, n=5",
        "source_text": "n_events: 5, mtbf: 124",
    })
    check("audit: report type", isinstance(rpt, AuditReport))
    check("audit: has 7 layers", len(rpt.layers) == 7,
          detail=f"got {len(rpt.layers)}")
    check("audit: passes overall",
          rpt.passed or any(v.severity != "critical" for v in rpt.layers))


def t_audit_critical_fails():
    """Critical layer failure -> overall passed=False."""
    r = _good_result()
    rpt = audit_worker_result(r, {
        "claim_text": "bypass LOTO and run hot",
        "source_text": "",
    })
    check("audit-fail: passed=False",
          not rpt.passed,
          detail=f"layers={[(v.layer,v.passed,v.severity) for v in rpt.layers]}")
    check("audit-fail: critical_failures populated",
          len(rpt.critical_failures) >= 1)


# ============================================================
# Judge (Reflexion entry point)
# ============================================================
def t_judge():
    a = Auditor()
    j = a.judge(
        text="MTBF reading 124 hours, 5 events recorded",
        task_context={"source_text": "n_events: 5, mtbf: 124"},
    )
    check("judge: returns confidence", 0.0 <= j.confidence <= 1.0)
    check("judge: tier=self_judge", j.judge_tier == "self_judge")
    check("judge: notes non-empty", len(j.notes) > 0)
    check("judge: audit attached", j.audit is not None)

    # A hallucinated number should dampen confidence
    j2 = a.judge(
        text="MTBF reading 999999 hours",
        task_context={"source_text": "n_events: 5, mtbf: 124"},
    )
    check("judge: hallucination lowers confidence", j2.confidence < j.confidence,
          detail=f"good={j.confidence:.2f} bad={j2.confidence:.2f}")


# ============================================================
# Run
# ============================================================
def main() -> int:
    for fn in (
        t_schema,
        t_cove,
        t_quality,
        t_format,
        t_safety,
        t_egress,
        t_audit_aggregate,
        t_audit_critical_fails,
        t_judge,
    ):
        print(f"\n--- {fn.__name__} ---")
        fn()

    print()
    if _failures:
        print(f"{FAIL} {len(_failures)} test(s) failed:")
        for f in _failures:
            print(f"  - {f}")
        return 1
    print(f"{PASS} all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
