"""
test_battery.py - fire a batch of real prompts at the orchestrator with persist=True
ref: MASTER_PLAN_v5.md s 15 (Night Cycle replay needs decision_log entries)

Differs from tests/test_orchestrator_flow.py:
  - Uses persist=True (default) so each session lands in decision_log/daily/<date>/
  - Captures wall-clock + best-effort VRAM via nvidia-smi
  - Writes a batch report to output/test_battery/<timestamp>.md
  - No PASS/FAIL gating - this is a soak test, not a regression test

Usage:
    .venv/Scripts/python.exe scripts/test_battery.py
    .venv/Scripts/python.exe scripts/test_battery.py --tag smoke-d1
    .venv/Scripts/python.exe scripts/test_battery.py --prompts custom_prompts.json
    .venv/Scripts/python.exe scripts/test_battery.py --skip-workers   # skip slow .docx/.xlsx prompts
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path

# UTF-8 stdout (Windows cp1252 trips on Thai)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Load .env so TPM_ORCHESTRATOR_MODEL etc. take effect
_env_file = REPO / ".env"
if _env_file.exists():
    for line in _env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from tpm_core.llm import health  # noqa: E402
from tpm_core.orchestrator import UI, run_orchestrator  # noqa: E402


# ============================================================
# MockUI - same shape as tests/test_orchestrator_flow.py
# ============================================================
class MockUI(UI):
    def __init__(self, answers):
        self.answers = deque(answers)
        self.questions_asked = []
        self.info_messages = []

    def ask(self, question, options):
        self.questions_asked.append((question, list(options)))
        if self.answers:
            return self.answers.popleft()
        return "yes"  # default-confirm if we exhaust the script

    def info(self, msg):
        self.info_messages.append(msg)


# ============================================================
# Default prompt set (D1 smoke - 10 prompts across 8 categories)
# ============================================================
DEFAULT_PROMPTS = [
    {
        "id": "lookup_en_astm",
        "category": "lookup_en",
        "prompt": "what is ASTM A106 standard",
        "ui_answers": ["yes"],
    },
    {
        "id": "lookup_th_oee",
        "category": "lookup_th",
        "prompt": "OEE คืออะไร อธิบายเป็นภาษาไทย",
        "ui_answers": ["yes"],
    },
    {
        "id": "lookup_en_mtbf",
        "category": "lookup_en",
        "prompt": "what is MTBF and MTTR difference",
        "ui_answers": ["yes"],
    },
    {
        "id": "lookup_th_5s",
        "category": "lookup_th",
        "prompt": "5S คืออะไร อธิบายเป็นไทย",
        "ui_answers": ["yes"],
    },
    {
        "id": "compare_fmea_fta",
        "category": "lookup_compare",
        "prompt": "FMEA vs FTA ต่างกันยังไง",
        "ui_answers": ["yes"],
    },
    {
        "id": "egress_boiler",
        "category": "egress_block",
        "prompt": "Boiler B-2 maintenance log incident report",
        "ui_answers": ["yes"],
    },
    {
        "id": "vague_clarify",
        "category": "vague",
        "prompt": "ตรวจของ",
        "ui_answers": ["ทำไปเลย"],  # user-override skip-clarify path
    },
    {
        "id": "skip_clarify",
        "category": "skip_clarify",
        "prompt": "fix it ทำไปเลย",
        "ui_answers": ["ทำไปเลย"],
    },
    {
        "id": "worker_report_makino",
        "category": "worker_report",
        "prompt": "เขียนรายงานการบำรุงรักษา MAKINO-a51nx 30 วันล่าสุด",
        "ui_answers": ["yes"],
        "is_worker": True,
    },
    {
        "id": "worker_excel_pareto",
        "category": "worker_excel",
        "prompt": "Excel Pareto chart downtime ของ SHIBAURA-EC100SX 60 วัน",
        "ui_answers": ["yes"],
        "is_worker": True,
    },
    # ---- D2 24-prompt battery additions (2026-05-12) ----
    # Calc worker (Phase 3 Day 3 - new this session)
    {
        "id": "calc_stress",
        "category": "calc",
        "prompt": "compute stress F=1000 N A=0.05 m^2",
        "ui_answers": ["yes"],
        "is_worker": True,
    },
    {
        "id": "calc_ohms_law",
        "category": "calc",
        "prompt": "ohm's law I=2 A R=10 ohm",
        "ui_answers": ["yes"],
        "is_worker": True,
    },
    {
        "id": "calc_cooling_time_th",
        "category": "calc",
        "prompt": "คำนวณ cooling time wall t=3 mm",
        "ui_answers": ["yes"],
        "is_worker": True,
    },
    {
        "id": "calc_clamping_force",
        "category": "calc",
        "prompt": "clamping force P=100 MPa A=0.01 m^2",
        "ui_answers": ["yes"],
        "is_worker": True,
    },
    # Mold defect lookups (Section 25)
    {
        "id": "lookup_defect_flash",
        "category": "lookup_mold",
        "prompt": "Flash defect ใน injection mold เกิดจากอะไร",
        "ui_answers": ["yes"],
    },
    {
        "id": "lookup_defect_sink",
        "category": "lookup_mold",
        "prompt": "sink mark ของชิ้นพลาสติกแก้ยังไง",
        "ui_answers": ["yes"],
    },
    {
        "id": "lookup_defect_burr",
        "category": "lookup_mold",
        "prompt": "Burr ใน press die เกิดจากสาเหตุอะไร",
        "ui_answers": ["yes"],
    },
    # Inquiry-First skip path (general knowledge / standard ref)
    {
        "id": "inquiry_skip_triz",
        "category": "inquiry_skip",
        "prompt": "TRIZ principle 35 คืออะไร อธิบายในภาษาไทย",
        "ui_answers": ["yes"],
    },
    {
        "id": "inquiry_skip_iso",
        "category": "inquiry_skip",
        "prompt": "ISO 9001:2015 มาตรฐานกำหนดอะไรเรื่อง maintenance",
        "ui_answers": ["yes"],
    },
    # Inquiry-First ASK path (user-specific subject)
    {
        "id": "inquiry_ask_pm",
        "category": "inquiry_ask",
        "prompt": "PM schedule ของ MAKINO V33 ครั้งล่าสุดเมื่อไร",
        "ui_answers": ["yes", "C"],   # confirm intent then inquiry -> search
    },
    {
        "id": "inquiry_ask_boiler",
        "category": "inquiry_ask",
        "prompt": "Boiler #2 ของเราซ่อมครั้งล่าสุดเมื่อไร",
        "ui_answers": ["yes", "C"],
    },
    # Material lookup (Section 25)
    {
        "id": "lookup_skd11",
        "category": "lookup_material",
        "prompt": "SKD11 hardness และ application คืออะไร",
        "ui_answers": ["yes"],
    },
    # Compound / edge cases
    {
        "id": "compare_skd",
        "category": "lookup_compare",
        "prompt": "SKD11 vs SKD61 ต่างกันยังไง ใช้งานต่างกันอย่างไร",
        "ui_answers": ["yes"],
    },
    {
        "id": "scientific_calc",
        "category": "calc",
        "prompt": "compute pressure with F=1.5e3 N and A=0.002 m^2",
        "ui_answers": ["yes"],
        "is_worker": True,
    },
]


# ============================================================
# VRAM helper (best-effort, soft-fail)
# ============================================================
def vram_used_mb():
    """Returns int MB used on first GPU, or None on failure."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4,
        )
        if out.returncode != 0:
            return None
        line = out.stdout.strip().splitlines()[0]
        return int(line.strip())
    except Exception:
        return None


# ============================================================
# Battery runner
# ============================================================
def run_one(spec, tag):
    """Run one prompt. Returns dict with timing/phase/files/session_id."""
    pid = spec["id"]
    prompt = spec["prompt"]
    answers = spec.get("ui_answers", ["yes"])

    print(f"  [{pid}] {prompt[:60]}{'...' if len(prompt) > 60 else ''}")

    ui = MockUI(answers=answers)
    vram_before = vram_used_mb()
    t0 = time.perf_counter()
    error = ""
    final = None
    try:
        final = run_orchestrator(prompt, ui=ui, persist=True)
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"
    dt = time.perf_counter() - t0
    vram_after = vram_used_mb()

    record = {
        "id": pid,
        "category": spec.get("category", "?"),
        "prompt": prompt,
        "tag": tag,
        "duration_s": round(dt, 2),
        "vram_before_mb": vram_before,
        "vram_after_mb": vram_after,
        "vram_delta_mb": (vram_after - vram_before) if (vram_before and vram_after) else None,
        "n_questions": len(ui.questions_asked) if ui else 0,
        "error": error,
    }

    if final is not None:
        record["phase"] = final.phase.value
        record["session_id"] = final.session_id
        record["started_at"] = final.started_at.isoformat() if final.started_at else None
        # final_output may have output_files / answer
        out_files = []
        if final.final_output:
            out_files = final.final_output.get("output_files", []) or []
        record["output_files"] = out_files
        # Surface first answer line if synthesized
        ans = ""
        if final.final_output:
            ans = final.final_output.get("answer", "") or ""
        record["answer_chars"] = len(ans)
        record["answer_preview"] = ans[:120].replace("\n", " ") if ans else ""
        record["state_error"] = final.error or ""
    else:
        record["phase"] = "CRASHED"
        record["session_id"] = None
        record["output_files"] = []
        record["answer_chars"] = 0
        record["answer_preview"] = ""
        record["state_error"] = ""

    icon = {
        "done": "[OK]",
        "failed": "[FAIL]",
        "clarify": "[STUCK]",
        "CRASHED": "[CRASH]",
    }.get(record["phase"], "[?]")
    print(f"      {icon} phase={record['phase']:8s} t={dt:5.1f}s session={record['session_id']}")
    if error:
        print(f"      err: {error}")
    return record


def write_report(records, tag, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = out_dir / f"battery_{tag}_{ts}.md"
    json_path = out_dir / f"battery_{tag}_{ts}.json"

    json_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    # Summary
    total = len(records)
    n_done = sum(1 for r in records if r["phase"] == "done")
    n_fail = sum(1 for r in records if r["phase"] == "failed")
    n_stuck = sum(1 for r in records if r["phase"] == "clarify")
    n_crash = sum(1 for r in records if r["phase"] == "CRASHED")
    total_s = sum(r["duration_s"] for r in records)

    lines = []
    lines.append(f"# Battery report: {tag}")
    lines.append("")
    lines.append(f"- Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Model: `{os.environ.get('TPM_ORCHESTRATOR_MODEL', 'qwen3:8b (default)')}`")
    lines.append(f"- Total: {total} | DONE: {n_done} | FAILED: {n_fail} | CLARIFY-stuck: {n_stuck} | CRASHED: {n_crash}")
    lines.append(f"- Wall-clock: {total_s:.1f}s ({total_s/60:.1f} min)")
    lines.append("")
    lines.append("## Per-prompt detail")
    lines.append("")
    lines.append("| id | cat | phase | t(s) | dVRAM | files | preview |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in records:
        files_str = ", ".join(Path(f).name for f in r["output_files"]) if r["output_files"] else "-"
        dvram = f"{r['vram_delta_mb']:+d}" if r.get("vram_delta_mb") is not None else "-"
        prev = (r.get("answer_preview") or r.get("error") or r.get("state_error") or "")[:60]
        prev = prev.replace("|", "\\|")
        lines.append(f"| {r['id']} | {r['category']} | {r['phase']} | {r['duration_s']} | {dvram} | {files_str} | {prev} |")
    lines.append("")
    lines.append("## Categories")
    lines.append("")
    by_cat = {}
    for r in records:
        by_cat.setdefault(r["category"], []).append(r)
    lines.append("| category | n | phases |")
    lines.append("|---|---|---|")
    for cat, rs in sorted(by_cat.items()):
        phases = ", ".join(sorted(set(rr["phase"] for rr in rs)))
        lines.append(f"| {cat} | {len(rs)} | {phases} |")
    lines.append("")
    lines.append("## Sessions persisted")
    lines.append("")
    sids = [r["session_id"] for r in records if r.get("session_id")]
    lines.append(f"- count: {len(sids)}")
    lines.append("- night_cycle.py will replay these on next run")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def main():
    p = argparse.ArgumentParser(description="TPM AI battery runner (real persist)")
    p.add_argument("--tag", default="smoke", help="label for the batch report filename")
    p.add_argument("--prompts", default=None, help="JSON file with prompt list (overrides default)")
    p.add_argument("--skip-workers", action="store_true", help="skip is_worker prompts (faster)")
    p.add_argument("--only", default=None, help="run only this prompt id (or comma-list)")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    for noisy in ("httpx", "httpcore", "urllib3", "wikipediaapi", "tpm_search"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    print("=" * 68)
    print(f"TPM AI Battery Runner (tag={args.tag})")
    print("=" * 68)

    if not health():
        print("[FAIL] Ollama not reachable. Run: ollama serve")
        return 2

    # Pick prompt set
    prompts = DEFAULT_PROMPTS
    if args.prompts:
        prompts = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    if args.skip_workers:
        prompts = [s for s in prompts if not s.get("is_worker")]
    if args.only:
        wanted = set(args.only.split(","))
        prompts = [s for s in prompts if s["id"] in wanted]
        if not prompts:
            print(f"[FAIL] no prompts matched --only={args.only}")
            return 2

    print(f"Model: {os.environ.get('TPM_ORCHESTRATOR_MODEL', 'qwen3:8b (default)')}")
    print(f"Prompts: {len(prompts)}")
    print()

    records = []
    t_start = time.perf_counter()
    for spec in prompts:
        try:
            r = run_one(spec, args.tag)
        except Exception as e:  # noqa: BLE001 - hard outer catch so battery survives
            r = {
                "id": spec["id"], "category": spec.get("category", "?"),
                "prompt": spec["prompt"], "tag": args.tag,
                "duration_s": 0.0, "phase": "CRASHED",
                "session_id": None, "error": f"runner-outer: {type(e).__name__}: {e}",
                "output_files": [], "answer_chars": 0, "answer_preview": "",
                "vram_before_mb": None, "vram_after_mb": None, "vram_delta_mb": None,
                "n_questions": 0, "state_error": "",
            }
            records.append(r)
            print(f"      [CRASH-OUTER] {r['error']}")
            continue
        records.append(r)
    t_total = time.perf_counter() - t_start

    out_dir = REPO / "output" / "test_battery"
    md_path, json_path = write_report(records, args.tag, out_dir)

    print()
    print("=" * 68)
    n_done = sum(1 for r in records if r["phase"] == "done")
    n_fail = sum(1 for r in records if r["phase"] == "failed")
    n_stuck = sum(1 for r in records if r["phase"] == "clarify")
    n_crash = sum(1 for r in records if r["phase"] == "CRASHED")
    print(f"Total: {len(records)} | DONE: {n_done} | FAILED: {n_fail} | CLARIFY-stuck: {n_stuck} | CRASHED: {n_crash}")
    print(f"Wall-clock: {t_total:.1f}s ({t_total/60:.1f} min)")
    print(f"Report: {md_path}")
    print(f"JSON:   {json_path}")
    print("Next: python scripts/night_cycle.py")
    print("=" * 68)

    return 0 if n_crash == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
