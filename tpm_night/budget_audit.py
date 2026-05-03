"""
tpm_night.budget_audit - prompt-size + runtime budget audit
ref: 3-framework debugging insight (May 2026) + MASTER_PLAN_v5.md "Context Budget Manager"

Two scans:
    audit_prompts() - static scan of every system prompt in the codebase
                      Flags any > 2000 chars (per Master Plan budget table).
                      Catches the OpenClaw "long prefill" pitfall before it bites.
    audit_runtime() - looks at saved sessions and computes:
                      - p50 / p90 / max latency
                      - cold-start frequency (first call > 30s)
                      - sessions where worker prompt revised > 2 times
                      - quota burn rate (Tavily / Exa)
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tpm_night.session_store import SessionRecord

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent

# Files we statically scan for system prompt strings
PROMPT_SOURCE_FILES = [
    "tpm_core/clarification.py",
    "tpm_workers/report.py",
    # Add more here as workers grow
]

# From MASTER_PLAN_v5.md "Context Budget Manager":
SYSTEM_PROMPT_LIMIT_CHARS = 2000


# ============================================================
# Static prompt audit
# ============================================================
@dataclass
class PromptFinding:
    file: str
    name: str            # variable name (e.g., "INTENT_PARSER_SYSTEM")
    chars: int
    severity: str        # "ok" | "warn" | "error"
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "name": self.name,
            "chars": self.chars,
            "severity": self.severity,
            "note": self.note,
        }


# Match `NAME_SYSTEM = """\n...\n"""` style strings
_PROMPT_RE = re.compile(
    r'(?P<name>[A-Z][A-Z0-9_]*_SYSTEM)\s*=\s*(?:r?"""|\'\'\')(?P<body>.*?)(?:"""|\'\'\')',
    re.DOTALL,
)


def audit_prompts(
    files: list[str] | None = None,
    char_limit: int = SYSTEM_PROMPT_LIMIT_CHARS,
) -> list[PromptFinding]:
    """
    Scan source files for system prompt strings, flag any over budget.
    Returns list of findings (errors first).
    """
    findings: list[PromptFinding] = []
    for relpath in (files or PROMPT_SOURCE_FILES):
        fpath = REPO_ROOT / relpath
        if not fpath.exists():
            continue
        text = fpath.read_text(encoding="utf-8", errors="replace")
        for match in _PROMPT_RE.finditer(text):
            name = match.group("name")
            body = match.group("body")
            chars = len(body.strip())
            if chars > char_limit:
                sev = "error" if chars > char_limit * 1.5 else "warn"
                note = (
                    f"prompt {chars} chars > limit {char_limit} - shrink or "
                    f"split (OpenClaw long-prefill anti-pattern)"
                )
            else:
                sev = "ok"
                note = ""
            findings.append(PromptFinding(
                file=relpath, name=name, chars=chars,
                severity=sev, note=note,
            ))
    findings.sort(key=lambda f: {"error": 0, "warn": 1, "ok": 2}[f.severity])
    return findings


# ============================================================
# Runtime audit - over saved sessions
# ============================================================
@dataclass
class RuntimeStats:
    n_sessions: int = 0
    n_done: int = 0
    n_failed: int = 0
    durations_ms: list[int] = field(default_factory=list)
    cold_starts: int = 0           # any session w/ first handoff > 30s
    high_latency: list[str] = field(default_factory=list)  # session ids w/ > p90 latency
    failure_modes: dict[str, int] = field(default_factory=dict)  # error -> count
    egress_blocks: int = 0
    auditor_findings: list[str] = field(default_factory=list)

    def p50(self) -> int:
        if not self.durations_ms:
            return 0
        s = sorted(self.durations_ms)
        return s[len(s) // 2]

    def p90(self) -> int:
        if not self.durations_ms:
            return 0
        s = sorted(self.durations_ms)
        return s[int(len(s) * 0.9)]

    def avg(self) -> int:
        if not self.durations_ms:
            return 0
        return sum(self.durations_ms) // len(self.durations_ms)

    def as_dict(self) -> dict[str, Any]:
        return {
            "n_sessions": self.n_sessions,
            "n_done": self.n_done,
            "n_failed": self.n_failed,
            "duration_p50_ms": self.p50(),
            "duration_p90_ms": self.p90(),
            "duration_avg_ms": self.avg(),
            "cold_starts": self.cold_starts,
            "high_latency_sessions": self.high_latency,
            "failure_modes": self.failure_modes,
            "egress_blocks": self.egress_blocks,
            "auditor_findings_count": len(self.auditor_findings),
        }


def audit_runtime(sessions: list[SessionRecord]) -> RuntimeStats:
    """Compute runtime stats over a batch of sessions."""
    stats = RuntimeStats(n_sessions=len(sessions))
    for s in sessions:
        if s.duration_ms > 0:
            stats.durations_ms.append(s.duration_ms)
        if s.final_phase == "done":
            stats.n_done += 1
        elif s.final_phase == "failed":
            stats.n_failed += 1
            # Categorize failure
            if "egress blocked" in (s.error or "").lower():
                stats.egress_blocks += 1
                stats.failure_modes["egress_blocked"] = stats.failure_modes.get("egress_blocked", 0) + 1
            elif "timeout" in (s.error or "").lower():
                stats.failure_modes["timeout"] = stats.failure_modes.get("timeout", 0) + 1
            elif s.error:
                key = s.error.split(":")[0][:40]
                stats.failure_modes[key] = stats.failure_modes.get(key, 0) + 1

        # Auditor findings from worker output
        af = (s.final_output or {}).get("auditor_findings", []) or []
        for f in af:
            stats.auditor_findings.append(f"{s.session_id[:6]}: {f}")

    # High-latency sessions = those above p90
    if stats.durations_ms:
        threshold = stats.p90()
        for s in sessions:
            if s.duration_ms > threshold:
                stats.high_latency.append(s.session_id)
                # cold-start heuristic - first chat call > 30s strongly suggests model load
                if s.duration_ms > 30_000 and s.handoff_log:
                    stats.cold_starts += 1
    return stats


# ============================================================
# Anti-pattern detection (frequency-based)
# ============================================================
def detect_repeated_failures(
    sessions: list[SessionRecord],
    min_count: int = 3,
) -> list[dict[str, Any]]:
    """
    Find user_request patterns that fail >= min_count times.
    Output candidates for new anti_patterns/.
    """
    failed = [s for s in sessions if s.final_phase == "failed"]
    by_request: dict[str, list[str]] = {}
    for s in failed:
        # Crude bucket: first 40 chars of request
        key = (s.user_request or "")[:40].lower().strip()
        if not key:
            continue
        by_request.setdefault(key, []).append(s.session_id)

    return [
        {
            "request_prefix": k,
            "count": len(v),
            "session_ids": v,
            "suggestion": "consider adding to .tpm_context/anti_patterns/",
        }
        for k, v in by_request.items() if len(v) >= min_count
    ]
