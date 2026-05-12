"""
tpm_workers.auditor - 8-layer audit framework (Section 12)
                    + judge backend for Reflexion N-round (Section 15.7)

7 of 8 layers implemented (Phoenix semantic eval deferred until Arize
infrastructure exists). All layers run without LLM calls so the auditor
is fast, deterministic, and safe under Bug #7 (OPENSSL_Uplink).

Layers:
    1. schema       - Pydantic structural validity of WorkerResult
    2. cove_numbers - numeric extraction + closest-match (§ 12.2 Strategy 1)
    3. quality      - non-empty, length, required notes
    4. format       - file-type heuristics for output_files
    5. safety       - hazard phrase / LOTO / dangerous-procedure scan
    6. confidence   - confidence breakdown shape (high_because / uncertain)
    7. egress       - re-classify output text (defense in depth)
    8. (deferred)   - semantic Phoenix eval

Public API:
    Auditor.audit(result, ctx) -> AuditReport
    Auditor.judge(text, ctx)   -> JudgeVerdict   (Reflexion § 15.7 Q3 tier 4)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from tpm_workers.base import WorkerResult, WorkerType

log = logging.getLogger(__name__)


# ============================================================
# Verdict shapes
# ============================================================
@dataclass
class LayerVerdict:
    layer: str
    passed: bool
    confidence: float = 1.0
    severity: str = "info"          # info | warn | critical
    findings: list[str] = field(default_factory=list)
    notes: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    passed: bool
    overall_confidence: float
    layers: list[LayerVerdict] = field(default_factory=list)

    @property
    def critical_failures(self) -> list[LayerVerdict]:
        return [v for v in self.layers if not v.passed and v.severity == "critical"]

    def summary_lines(self) -> list[str]:
        lines = [f"audit: passed={self.passed} confidence={self.overall_confidence:.2f}"]
        for v in self.layers:
            mark = "OK" if v.passed else ("X" if v.severity == "critical" else "?")
            lines.append(f"  [{mark}] {v.layer:14s} conf={v.confidence:.2f} {v.findings or ''}")
        return lines


@dataclass
class JudgeVerdict:
    """Returned by Auditor.judge() — used by Reflexion (§ 15.7 Q3 tier 4)."""
    confidence: float
    notes: list[str]
    judge_tier: str = "self_judge"   # tier 4 in the § 15.7 waterfall
    audit: Optional[AuditReport] = None


# ============================================================
# Layers (deterministic, no LLM)
# ============================================================
def layer_schema(result: WorkerResult, ctx: dict[str, Any]) -> LayerVerdict:
    """Layer 1: structural Pydantic validity."""
    findings: list[str] = []
    if result.worker_type is None:
        findings.append("worker_type missing")
    if not isinstance(result.success, bool):
        findings.append("success must be bool")
    if not isinstance(result.output_files, list):
        findings.append("output_files must be list")
    return LayerVerdict(
        layer="schema",
        passed=not findings,
        severity="critical" if findings else "info",
        findings=findings,
    )


_NUMBER_RE = re.compile(r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?")


def _extract_numbers(text: str) -> list[float]:
    out: list[float] = []
    for m in _NUMBER_RE.finditer(text or ""):
        try:
            out.append(float(m.group(0)))
        except ValueError:
            pass
    return out


def _closest(target: float, candidates: list[float], rel_tol: float = 0.005) -> Optional[float]:
    if not candidates:
        return None
    best, best_diff = None, float("inf")
    for c in candidates:
        d = abs(target - c)
        if d < best_diff and d <= rel_tol * max(abs(target), 1.0):
            best, best_diff = c, d
    return best


def layer_cove_numbers(result: WorkerResult, ctx: dict[str, Any]) -> LayerVerdict:
    """
    Layer 2: numeric CoVe (Section 12.2 Strategy 1).

    For each number that appears in the worker output, check it can be found
    in the trusted source (ctx['source_text']) within 0.5% tolerance.

    For Report worker, source_text = the researcher payload (raw data).
    For Calc worker, source_text = inputs + computed result (always consistent).

    When source_text is absent (worker didn't supply one), this layer skips.
    """
    source_text = ctx.get("source_text") or ""
    claim_text = ctx.get("claim_text") or ""
    if not source_text or not claim_text:
        return LayerVerdict(layer="cove_numbers", passed=True,
                            notes={"skipped": "no source/claim text"})

    claimed = _extract_numbers(claim_text)
    sourced = _extract_numbers(source_text)
    if not claimed:
        return LayerVerdict(layer="cove_numbers", passed=True,
                            notes={"skipped": "no numbers claimed"})

    unverified: list[float] = []
    for c in claimed:
        if _closest(c, sourced) is None:
            unverified.append(c)

    findings: list[str] = []
    severity = "info"
    if unverified:
        # Allow a small tolerance: up to 1 unverified number out of 5 is "warn",
        # more than that is "critical" (possible hallucination)
        rate = len(unverified) / max(len(claimed), 1)
        severity = "critical" if rate > 0.20 else "warn"
        findings.append(
            f"{len(unverified)}/{len(claimed)} claimed numbers not in source: "
            f"{unverified[:5]}"
        )
    return LayerVerdict(
        layer="cove_numbers",
        passed=not unverified,
        confidence=1.0 - 0.5 * len(unverified) / max(len(claimed), 1),
        severity=severity,
        findings=findings,
        notes={"claimed": len(claimed), "sourced": len(sourced),
               "unverified": len(unverified)},
    )


def layer_quality(result: WorkerResult, ctx: dict[str, Any]) -> LayerVerdict:
    """Layer 3: minimal-content / completeness checks."""
    findings: list[str] = []
    if not result.summary:
        findings.append("summary empty")
    if result.worker_type != WorkerType.CALC and not result.output_files and result.success:
        findings.append("output_files empty despite success=True")
    if not result.steps:
        findings.append("no steps recorded")
    severity = "warn" if findings else "info"
    return LayerVerdict(
        layer="quality",
        passed=not findings,
        confidence=1.0 if not findings else 0.7,
        severity=severity,
        findings=findings,
    )


_FORMAT_MIN_BYTES = {
    ".docx": 5_000,
    ".xlsx": 4_000,
    ".pptx": 5_000,
    ".pdf": 1_000,
    ".md": 50,
}


def layer_format(result: WorkerResult, ctx: dict[str, Any]) -> LayerVerdict:
    """Layer 4: file-type sanity (size floors for each format)."""
    from pathlib import Path

    findings: list[str] = []
    for fp in result.output_files:
        p = Path(fp)
        if not p.exists():
            findings.append(f"file missing: {fp}")
            continue
        floor = _FORMAT_MIN_BYTES.get(p.suffix.lower(), 0)
        if floor and p.stat().st_size < floor:
            findings.append(
                f"{p.name} too small ({p.stat().st_size}B < {floor}B floor for {p.suffix})"
            )
    severity = "warn" if findings else "info"
    return LayerVerdict(
        layer="format",
        passed=not findings,
        severity=severity,
        findings=findings,
    )


# Hazard phrases (Section 9.1.3 - Safety > Efficiency). Trigger a warn-level
# finding to suggest human review when an output contains these without a
# safety annotation nearby.
_HAZARD_PATTERNS = {
    # Danger: instruction to bypass/skip LOTO. Mitigation: explicit negation
    # nearby ("do not bypass", "ห้าม bypass"). The mitigation MUST be a
    # negation phrase, not just any LOTO mention - "bypass LOTO" alone is
    # always bad regardless of what other LOTO words are in the same sentence.
    "loto_missing": (
        r"\b(?:bypass|skip|disable|ข้าม)\s+(?:the\s+)?(?:LOTO|lockout|ล็อกเอาท์)\b",
        r"\b(?:do\s*not|don't|never|ห้าม)\s+(?:bypass|skip|disable|ข้าม)\b",
    ),
    "hot_work": (
        r"\b(?:hot\s*work|งานร้อน|เชื่อม.{0,10}ใกล้.{0,10}ก๊าซ|welding\s+near\s+gas)\b",
        r"\b(?:hot\s*work\s*permit|gas\s*check|ตรวจเช็คก๊าซ|with\s+permit)\b",
    ),
    "no_ppe": (
        r"\b(?:ไม่ต้องใส่\s*PPE|ไม่ต้องสวม.{0,10}ป้องกัน|skip\s+PPE|no\s+PPE\s+required)\b",
        None,
    ),
}


def layer_safety(result: WorkerResult, ctx: dict[str, Any]) -> LayerVerdict:
    """Layer 5: hazard-phrase scan with annotation context."""
    text = (ctx.get("claim_text") or result.summary or "")
    findings: list[str] = []
    for tag, (danger_re, mitigation_re) in _HAZARD_PATTERNS.items():
        if re.search(danger_re, text, flags=re.IGNORECASE):
            if mitigation_re and re.search(mitigation_re, text, flags=re.IGNORECASE):
                continue  # mitigation present nearby
            findings.append(f"hazard:{tag}")
    return LayerVerdict(
        layer="safety",
        passed=not findings,
        severity="critical" if findings else "info",
        confidence=1.0 - 0.3 * len(findings),
        findings=findings,
    )


def layer_confidence(result: WorkerResult, ctx: dict[str, Any]) -> LayerVerdict:
    """
    Layer 7: shape of confidence breakdown (Section 10.3 handoff packet).
    Currently a soft check — flag if confidence is too rosy without any
    handoff_log entry to back it up.
    """
    findings: list[str] = []
    if result.confidence > 0.9 and not result.auditor_findings and not result.steps:
        findings.append("confidence > 0.9 but no steps logged - suspicious")
    return LayerVerdict(
        layer="confidence",
        passed=not findings,
        confidence=result.confidence if result.confidence else 0.5,
        severity="warn" if findings else "info",
        findings=findings,
    )


def layer_egress(result: WorkerResult, ctx: dict[str, Any]) -> LayerVerdict:
    """
    Layer 8: re-classify the output text against egress rules
    (defense in depth — the L3 / worker-dispatch gates run earlier).
    """
    try:
        from tpm_search.egress import classify
        from tpm_search.types import Classification
    except ImportError:
        return LayerVerdict(layer="egress", passed=True,
                            notes={"skipped": "egress module unavailable"})

    text = (ctx.get("claim_text") or "") + " " + (result.summary or "")
    cls = classify(text)
    blocked = cls in (Classification.CONFIDENTIAL, Classification.RESTRICTED)
    findings = [f"classification={cls.value}"] if blocked else []
    return LayerVerdict(
        layer="egress",
        passed=not blocked,
        severity="critical" if blocked else "info",
        findings=findings,
        notes={"classification": cls.value},
    )


# ============================================================
# Default layer pipeline
# ============================================================
LayerFn = Callable[[WorkerResult, dict[str, Any]], LayerVerdict]

DEFAULT_LAYERS: list[LayerFn] = [
    layer_schema,
    layer_cove_numbers,
    layer_quality,
    layer_format,
    layer_safety,
    layer_confidence,
    layer_egress,
]

# Layer 6 (semantic / Phoenix) intentionally deferred — see module docstring.


# ============================================================
# Auditor
# ============================================================
class Auditor:
    """
    Run a set of layers against a WorkerResult + context dict, aggregate.
    No LLM call — pure Python (deterministic, fast, ~ms latency).
    """

    def __init__(self, layers: Optional[list[LayerFn]] = None):
        self.layers = layers or list(DEFAULT_LAYERS)

    def audit(
        self,
        result: WorkerResult,
        ctx: Optional[dict[str, Any]] = None,
    ) -> AuditReport:
        ctx = ctx or {}
        verdicts: list[LayerVerdict] = []
        for layer in self.layers:
            try:
                v = layer(result, ctx)
            except Exception as e:  # noqa: BLE001
                log.warning("auditor layer %s raised: %s", layer.__name__, e)
                v = LayerVerdict(
                    layer=getattr(layer, "__name__", "?"),
                    passed=False, severity="warn",
                    findings=[f"layer raised: {e}"],
                )
            verdicts.append(v)

        critical_fail = any(not v.passed and v.severity == "critical" for v in verdicts)
        if verdicts:
            overall_conf = sum(v.confidence for v in verdicts) / len(verdicts)
        else:
            overall_conf = 0.0
        return AuditReport(
            passed=not critical_fail,
            overall_confidence=overall_conf,
            layers=verdicts,
        )

    def judge(self, text: str, task_context: dict[str, Any]) -> JudgeVerdict:
        """
        Reflexion (§ 15.7 Q3 tier 4) judge entry point. Treats the candidate
        answer as a synthetic WorkerResult and runs the deterministic layers
        that don't require file output.

        task_context should include 'source_text' (the trusted source) for
        the numeric-CoVe layer to be meaningful.
        """
        synth = WorkerResult(
            worker_type=WorkerType.CALC,    # placeholder type
            success=True,
            output_files=[],
            summary=text[:500],
            steps=[],
            confidence=0.5,
        )
        ctx = dict(task_context)
        ctx.setdefault("claim_text", text)

        # Only use the layers that make sense for a free-text candidate
        text_layers = [
            layer_schema,
            layer_cove_numbers,
            layer_safety,
            layer_confidence,
            layer_egress,
        ]
        sub = Auditor(layers=text_layers)
        report = sub.audit(synth, ctx)

        notes: list[str] = []
        for v in report.layers:
            if v.findings:
                notes.append(f"{v.layer}: {'; '.join(v.findings)}")
            else:
                notes.append(f"{v.layer}: ok")

        return JudgeVerdict(
            confidence=report.overall_confidence,
            notes=notes,
            judge_tier="self_judge",
            audit=report,
        )


# ============================================================
# Convenience
# ============================================================
def audit_worker_result(
    result: WorkerResult,
    ctx: Optional[dict[str, Any]] = None,
) -> AuditReport:
    return Auditor().audit(result, ctx)
