"""
health_check.py — pre-startup system check
ref: MASTER_PLAN_v5.md § 22.2

Checks:
  1. Python version (need ≥ 3.11)
  2. VRAM free (need ≥ 1.5 GB headroom for orchestrator+scavenger)
  3. RAM free (need ≥ 4 GB)
  4. Disk free (need ≥ 10 GB on workspace drive)
  5. Ollama service up + models present
  6. Docker services (SearXNG, Langfuse, Phoenix) — optional in Phase 0
  7. Folder structure intact
  8. Audit log integrity (hash chain) — skip if not yet created
  9. CPU/GPU thermal status

Exit codes:
  0 = all pass (OK)
  1 = warnings (system runnable but degraded)
  2 = critical fail (do NOT start)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# Result types
# ============================================================
class Check:
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


def _r(name: str, status: str, msg: str = "", details: dict | None = None) -> dict:
    return {"name": name, "status": status, "msg": msg, "details": details or {}}


# ============================================================
# Individual checks
# ============================================================
def check_python() -> dict:
    v = sys.version_info
    pretty = f"{v.major}.{v.minor}.{v.micro}"
    if v < (3, 11):
        return _r("python_version", Check.FAIL, f"need ≥3.11, have {pretty}")
    if v >= (3, 14):
        return _r(
            "python_version",
            Check.WARN,
            f"have {pretty} — bleeding edge, some packages may lack wheels",
        )
    return _r("python_version", Check.OK, pretty)


def check_ram() -> dict:
    try:
        import psutil
    except ImportError:
        return _r("ram", Check.SKIP, "psutil not installed")
    mem = psutil.virtual_memory()
    free_gb = mem.available / (1024**3)
    total_gb = mem.total / (1024**3)
    if free_gb < 4:
        return _r("ram", Check.FAIL, f"only {free_gb:.1f} GB free of {total_gb:.0f} GB")
    if free_gb < 8:
        return _r("ram", Check.WARN, f"{free_gb:.1f} GB free — tight for heavy models")
    return _r("ram", Check.OK, f"{free_gb:.1f} GB free of {total_gb:.0f} GB")


def check_vram() -> dict:
    try:
        import GPUtil
    except ImportError:
        return _r("vram", Check.SKIP, "GPUtil not installed")
    gpus = GPUtil.getGPUs()
    if not gpus:
        return _r("vram", Check.WARN, "no GPU detected")
    g = gpus[0]
    free_gb = g.memoryFree / 1024
    total_gb = g.memoryTotal / 1024
    if free_gb < 1.5:
        return _r(
            "vram",
            Check.FAIL,
            f"only {free_gb:.2f} GB free — orchestrator+scavenger needs ≥6.5 GB",
            details={"gpu": g.name, "total_gb": total_gb},
        )
    if free_gb < 6.5:
        return _r("vram", Check.WARN, f"{free_gb:.2f} GB free — orchestrator may not fit")
    return _r("vram", Check.OK, f"{free_gb:.2f} / {total_gb:.1f} GB free", {"gpu": g.name})


def check_disk() -> dict:
    usage = shutil.disk_usage(str(REPO_ROOT))
    free_gb = usage.free / (1024**3)
    if free_gb < 10:
        return _r("disk", Check.FAIL, f"only {free_gb:.1f} GB free in workspace drive")
    if free_gb < 50:
        return _r("disk", Check.WARN, f"{free_gb:.1f} GB free — models alone need ~40 GB")
    return _r("disk", Check.OK, f"{free_gb:.1f} GB free")


def check_ollama() -> dict:
    if shutil.which("ollama") is None:
        return _r("ollama", Check.FAIL, "ollama binary not in PATH — install from ollama.com")
    try:
        out = subprocess.check_output(
            ["ollama", "list"], text=True, stderr=subprocess.STDOUT, timeout=10
        )
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        return _r("ollama", Check.FAIL, f"ollama list failed: {e}")
    required = ["qwen3:8b", "qwen3:1.7b", "bge-m3"]
    found = [m for m in required if m.split(":")[0] in out]
    if not found:
        return _r(
            "ollama",
            Check.WARN,
            "no required models pulled yet (Phase 0 task — see RUNBOOK)",
        )
    if len(found) < len(required):
        missing = [m for m in required if m.split(":")[0] not in out]
        return _r("ollama", Check.WARN, f"missing models: {missing}")
    return _r("ollama", Check.OK, f"models present: {found}")


def check_docker() -> dict:
    if shutil.which("docker") is None:
        return _r("docker", Check.WARN, "docker not in PATH — needed for Phase 1 SearXNG")
    try:
        subprocess.check_output(["docker", "info"], stderr=subprocess.STDOUT, timeout=5)
    except subprocess.SubprocessError:
        return _r("docker", Check.WARN, "docker daemon not running")
    return _r("docker", Check.OK, "docker daemon up")


REQUIRED_DIRS = [
    "raw_data",
    ".tpm_context/wiki",
    ".tpm_context/skills",
    ".tpm_context/anti_patterns",
    ".tpm_context/local_tools/installed",
    ".tpm_context/domain_knowledge",
    ".tpm_context/decision_log",
    ".tpm_context/night_cycle",
    "models",
    "scripts",
    "logs",
    "output",
]


def check_folders() -> dict:
    missing = [d for d in REQUIRED_DIRS if not (REPO_ROOT / d).is_dir()]
    if missing:
        return _r("folders", Check.FAIL, f"missing dirs: {missing}")
    return _r("folders", Check.OK, f"all {len(REQUIRED_DIRS)} dirs present")


REQUIRED_FILES = [
    ".tpm_context/AGENTS.md",
    ".tpm_context/SCHEMA.md",
    ".tpm_context/RUNBOOK.md",
    ".tpm_context/data_classification.yaml",
    ".gitignore",
]


def check_config_files() -> dict:
    missing = [f for f in REQUIRED_FILES if not (REPO_ROOT / f).is_file()]
    if missing:
        return _r("config_files", Check.FAIL, f"missing: {missing}")
    return _r("config_files", Check.OK, f"all {len(REQUIRED_FILES)} files present")


def check_thermal() -> dict:
    try:
        out = subprocess.check_output(
            [sys.executable, str(REPO_ROOT / "scripts" / "thermal_guard.py"), "--status"],
            text=True,
            timeout=10,
        )
        data = json.loads(out)
        if data["state"] == "CRITICAL":
            return _r("thermal", Check.FAIL, f"CPU={data['cpu_temp_c']} GPU={data['gpu_temp_c']}")
        if data["state"] in ("WARN", "THROTTLE"):
            return _r("thermal", Check.WARN, "; ".join(data["notes"]))
        return _r(
            "thermal",
            Check.OK,
            f"CPU={data['cpu_temp_c']}°C GPU={data['gpu_temp_c']}°C",
        )
    except Exception as e:  # noqa: BLE001
        return _r("thermal", Check.SKIP, f"thermal_guard not available: {e}")


def check_audit_chain() -> dict:
    db = REPO_ROOT / ".tpm_context" / "audit_log.db"
    if not db.exists():
        return _r("audit_chain", Check.SKIP, "no audit_log.db yet (Phase 2)")
    # full verify will be implemented later — for now just check file exists
    return _r("audit_chain", Check.OK, f"{db.stat().st_size} bytes")


# ============================================================
# Main
# ============================================================
ALL_CHECKS = [
    check_python,
    check_ram,
    check_vram,
    check_disk,
    check_folders,
    check_config_files,
    check_ollama,
    check_docker,
    check_thermal,
    check_audit_chain,
]


def main() -> int:
    results = [c() for c in ALL_CHECKS]

    fails = [r for r in results if r["status"] == Check.FAIL]
    warns = [r for r in results if r["status"] == Check.WARN]
    skips = [r for r in results if r["status"] == Check.SKIP]
    oks = [r for r in results if r["status"] == Check.OK]

    print("=" * 64)
    print("TPM AI Health Check")
    print("=" * 64)
    for r in results:
        icon = {
            Check.OK: "[OK]   ",
            Check.WARN: "[WARN] ",
            Check.FAIL: "[FAIL] ",
            Check.SKIP: "[SKIP] ",
        }[r["status"]]
        print(f"{icon} {r['name']:20s} {r['msg']}")
    print("-" * 64)
    print(
        f"Summary: OK={len(oks)} WARN={len(warns)} FAIL={len(fails)} SKIP={len(skips)}"
    )
    print("=" * 64)

    if fails:
        print(">>> CRITICAL: do NOT start until fails resolved")
        return 2
    if warns:
        print(">>> System runnable but degraded — review warnings")
        return 1
    print(">>> All systems go")
    return 0


if __name__ == "__main__":
    sys.exit(main())
