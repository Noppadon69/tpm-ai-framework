"""
tpm_night.morning_brief - render a Markdown brief
ref: MASTER_PLAN_v5.md § 14.6, § 15.4

Brief format (matches plan):
    🔍 Patterns found overnight
    📊 System work last night (replays + drift)
    ⚠️ Findings to approve
    🎯 Suggested actions
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from tpm_night.budget_audit import (
    PromptFinding,
    RuntimeStats,
    detect_repeated_failures,
)
from tpm_night.discrepancy import Discrepancy
from tpm_night.session_store import SessionRecord

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
BRIEF_DIR = REPO_ROOT / ".tpm_context" / "night_cycle" / "morning_brief"


def render_brief(
    *,
    date: str,
    sessions: list[SessionRecord],
    runtime_stats: RuntimeStats,
    prompt_findings: list[PromptFinding],
    replay_results: list[dict[str, Any]],
    quota_snapshot: Optional[dict[str, Any]] = None,
    reflexion_outcomes: Optional[list[Any]] = None,
) -> str:
    """Returns a single Markdown string."""
    out: list[str] = []
    out.append(f"# Morning Brief — {date}")
    out.append("")
    out.append(f"_Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}_")
    out.append("")

    # ---- Section 1: System work overnight ----
    out.append("## 📊 ระบบทำงานเมื่อคืน")
    out.append("")
    out.append(f"- Sessions วันนี้: **{runtime_stats.n_sessions}** "
               f"(✅ {runtime_stats.n_done} done / ❌ {runtime_stats.n_failed} failed)")
    if runtime_stats.durations_ms:
        out.append(
            f"- Latency: p50=`{runtime_stats.p50()/1000:.1f}s` "
            f"p90=`{runtime_stats.p90()/1000:.1f}s` "
            f"avg=`{runtime_stats.avg()/1000:.1f}s`"
        )
    out.append(f"- Cold-starts: **{runtime_stats.cold_starts}** "
               f"(>30s first call - probably model swap)")
    out.append(f"- Egress blocks: **{runtime_stats.egress_blocks}**")
    out.append(f"- Replays attempted: **{len(replay_results)}**")
    if quota_snapshot:
        tav = quota_snapshot.get("tavily", {})
        exa = quota_snapshot.get("exa", {})
        out.append(f"- Tavily quota: `{tav.get('used',0)}/1000` "
                   f"(remaining {tav.get('remaining','?')})")
        out.append(f"- Exa quota:    `{exa.get('used',0)}/1000` "
                   f"(remaining {exa.get('remaining','?')})")
    out.append("")

    # ---- Section 2: Replay discrepancies ----
    out.append("## 🔍 Replay discrepancies")
    out.append("")
    if not replay_results:
        out.append("- ไม่มี replay เมื่อคืน (หรือ session ทั้งหมดเป็น lookup สั้นๆ)")
    else:
        any_diff = False
        for r in replay_results:
            session_id = r.get("session_id", "?")[:8]
            request = (r.get("user_request") or "")[:60]
            diffs: list[Discrepancy] = r.get("discrepancies", [])
            errors = [d for d in diffs if d.severity == "error"]
            warns = [d for d in diffs if d.severity == "warn"]
            if errors or warns:
                any_diff = True
                icon = "❌" if errors else "⚠️"
                out.append(f"### {icon} `{session_id}` — {request!r}")
                for d in errors + warns:
                    out.append(
                        f"- **{d.field}**: `{d.original}` → `{d.replay}`  ({d.severity})"
                    )
                    if d.hint:
                        out.append(f"    > 💡 {d.hint}")
                out.append("")
        if not any_diff:
            out.append("- ✅ ทุก replay ตรงกับ original (ระบบเสถียร)")
    out.append("")

    # ---- Section 3: Prompt budget audit (the OpenClaw guard) ----
    out.append("## ⚠️ Prompt budget audit")
    out.append("")
    over_budget = [f for f in prompt_findings if f.severity in ("warn", "error")]
    if not over_budget:
        out.append("- ✅ ทุก system prompt อยู่ในงบ (≤ 2000 chars)")
    else:
        for f in over_budget:
            icon = "❌" if f.severity == "error" else "⚠️"
            out.append(f"- {icon} `{f.file}::{f.name}` — **{f.chars} chars**")
            if f.note:
                out.append(f"    > {f.note}")
    out.append("")

    # ---- Section 4: Anti-pattern detection ----
    out.append("## 🚨 Repeated failures (anti-pattern candidates)")
    out.append("")
    repeated = detect_repeated_failures(sessions, min_count=3)
    if not repeated:
        out.append("- ✅ ไม่มี request ที่ fail ซ้ำ ≥ 3 ครั้ง")
    else:
        for r in repeated:
            out.append(f"- `{r['request_prefix']!r}` failed **{r['count']}** times")
            out.append(f"    > {r['suggestion']}")
    out.append("")

    # ---- Section 4.5: Reflexion outcomes (Section 15.7 Phase 1 = brief only) ----
    if reflexion_outcomes:
        try:
            from tpm_reflexion.reflexion import format_outcome_for_brief
            out.append("## 🔁 Reflexion outcomes")
            out.append("")
            for i, outcome in enumerate(reflexion_outcomes, 1):
                # Each outcome is a ReflexionOutcome; format_outcome_for_brief
                # already produces a complete markdown block per outcome.
                label = getattr(outcome, "_label", f"task-{i}")
                out.append(format_outcome_for_brief(outcome, task_label=str(label)))
                out.append("")
        except ImportError:
            # tpm_reflexion not installed - silently skip (not a hard dep)
            pass

    # ---- Section 5: Auditor findings ----
    if runtime_stats.auditor_findings:
        out.append("## 🔎 Auditor findings (worker output review)")
        out.append("")
        for f in runtime_stats.auditor_findings[:10]:
            out.append(f"- {f}")
        if len(runtime_stats.auditor_findings) > 10:
            out.append(f"_... และอีก {len(runtime_stats.auditor_findings)-10} รายการ_")
        out.append("")

    # ---- Section 6: Suggested actions ----
    out.append("## 🎯 ข้อเสนอแนะ (รอ approve)")
    out.append("")
    suggestions = []
    if runtime_stats.cold_starts >= 3:
        suggestions.append(
            "เพิ่ม model preload ใน `start.sh` (cold-start ≥ 3 ครั้ง — เสียเวลา)"
        )
    if over_budget:
        suggestions.append(
            f"ลด/แบ่ง system prompt {len(over_budget)} ตัวที่เกินงบ"
        )
    if runtime_stats.failure_modes:
        top_failure = max(runtime_stats.failure_modes.items(), key=lambda x: x[1])
        suggestions.append(
            f"investigate failure pattern: `{top_failure[0]}` ({top_failure[1]} ครั้ง)"
        )
    if quota_snapshot:
        for prov in ("tavily", "exa"):
            q = quota_snapshot.get(prov, {})
            if q.get("soft_limited"):
                suggestions.append(f"⚠️ {prov} quota ใกล้หมด — ลด fallback หรือเพิ่ม cache")
    if not suggestions:
        suggestions.append("ไม่มีข้อเสนอแนะใหม่ - ระบบทำงานปกติ")
    for s in suggestions:
        out.append(f"- {s}")
    out.append("")

    # ---- Footer ----
    out.append("---")
    out.append("")
    out.append("📂 **Where to look:**")
    out.append("- Sessions: `.tpm_context/decision_log/daily/" + date + "/`")
    out.append("- Replays:  `.tpm_context/night_cycle/replays/`")
    out.append("- This brief: `.tpm_context/night_cycle/morning_brief/" + date + ".md`")
    return "\n".join(out)


def write_brief(date: str, content: str) -> Path:
    """Save brief to disk + return path."""
    BRIEF_DIR.mkdir(parents=True, exist_ok=True)
    path = BRIEF_DIR / f"{date}.md"
    path.write_text(content, encoding="utf-8")
    log.info("morning brief written: %s", path)
    return path
