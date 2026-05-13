"""
tests/test_pm_log.py - unit tests for tpm_mold.pm_log (Section 25.2.5)

Verifies:
  - register/append round-trip via JSONL
  - status_for() aggregates correctly
  - shots_between_pm computes deltas
  - defect_breakdown counts by type
  - events_in_range time filters

Uses a tmp dir override so the real .tpm_context/pm_log/ is untouched.

Run:
    .venv/Scripts/python.exe tests/test_pm_log.py
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

import tpm_mold.pm_log as pm  # noqa: E402

PASS = "[PASS]"
FAIL = "[FAIL]"
_failures: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"{PASS} {name}")
    else:
        print(f"{FAIL} {name}  {detail}")
        _failures.append(name)


def t_register_and_load():
    with tempfile.TemporaryDirectory() as td:
        pm.PM_LOG_DIR = Path(td)
        ev = pm.register_mold("TEST-001", material="P20", operator="alice")
        check("reg: event returned", ev.action == "register" and ev.shot_count == 0)
        check("reg: file created", (Path(td) / "TEST-001.jsonl").exists())
        events = pm.load_events("TEST-001")
        check("load: round-trip", len(events) == 1 and events[0].material == "P20")


def t_append_multiple():
    with tempfile.TemporaryDirectory() as td:
        pm.PM_LOG_DIR = Path(td)
        pm.register_mold("TEST-002", material="SKD11")
        pm.append_event(pm.PMEvent(mold_id="TEST-002", timestamp="2026-05-01T08:00:00+00:00",
                                   action="clean", shot_count=10000))
        pm.append_event(pm.PMEvent(mold_id="TEST-002", timestamp="2026-05-08T08:00:00+00:00",
                                   action="clean", shot_count=20000))
        pm.append_event(pm.PMEvent(mold_id="TEST-002", timestamp="2026-05-09T08:00:00+00:00",
                                   action="defect", defect_type="sink_mark", shot_count=20500))
        events = pm.load_events("TEST-002")
        check("multi: 4 events loaded", len(events) == 4)


def t_status_for():
    with tempfile.TemporaryDirectory() as td:
        pm.PM_LOG_DIR = Path(td)
        pm.register_mold("TEST-003", material="NAK80")
        pm.append_event(pm.PMEvent(mold_id="TEST-003", timestamp="2026-05-01T00:00:00+00:00",
                                   action="clean", shot_count=5000))
        pm.append_event(pm.PMEvent(mold_id="TEST-003", timestamp="2026-05-02T00:00:00+00:00",
                                   action="defect", defect_type="flash", shot_count=5500))
        pm.append_event(pm.PMEvent(mold_id="TEST-003", timestamp="2026-05-03T00:00:00+00:00",
                                   action="repair", part_replaced="ejector pin", shot_count=5500))
        st = pm.status_for("TEST-003")
        check("status: material",  st.material == "NAK80")
        check("status: shots",     st.cumulative_shots == 5500)
        check("status: defects=1", st.defects_logged == 1)
        check("status: repairs=1", st.repairs_logged == 1)
        check("status: last action=repair", st.last_action == "repair")
        check("status: last PM shots=5500", st.last_pm_shots == 5500)


def t_shots_between_pm():
    with tempfile.TemporaryDirectory() as td:
        pm.PM_LOG_DIR = Path(td)
        pm.register_mold("TEST-004", material="P20")
        pm.append_event(pm.PMEvent(mold_id="TEST-004", timestamp="2026-04-01T00:00:00+00:00",
                                   action="clean", shot_count=10000))
        pm.append_event(pm.PMEvent(mold_id="TEST-004", timestamp="2026-04-15T00:00:00+00:00",
                                   action="clean", shot_count=22000))
        pm.append_event(pm.PMEvent(mold_id="TEST-004", timestamp="2026-04-29T00:00:00+00:00",
                                   action="clean", shot_count=35000))
        deltas = pm.shots_between_pm("TEST-004")
        check("deltas: 2 intervals", len(deltas) == 2)
        check("deltas: first = 12000", deltas[0] == 12000)
        check("deltas: second = 13000", deltas[1] == 13000)


def t_defect_breakdown():
    with tempfile.TemporaryDirectory() as td:
        pm.PM_LOG_DIR = Path(td)
        pm.register_mold("TEST-005", material="SKD61")
        for t, dt in [
            ("2026-05-01T00:00:00+00:00", "flash"),
            ("2026-05-02T00:00:00+00:00", "flash"),
            ("2026-05-03T00:00:00+00:00", "sink_mark"),
            ("2026-05-04T00:00:00+00:00", "burr"),
            ("2026-05-05T00:00:00+00:00", "flash"),
        ]:
            pm.append_event(pm.PMEvent(mold_id="TEST-005", timestamp=t,
                                       action="defect", defect_type=dt))
        bd = pm.defect_breakdown("TEST-005")
        check("breakdown: 3 distinct", len(bd) == 3)
        check("breakdown: flash=3", bd["flash"] == 3)
        check("breakdown: sink_mark=1", bd["sink_mark"] == 1)


def t_events_in_range():
    with tempfile.TemporaryDirectory() as td:
        pm.PM_LOG_DIR = Path(td)
        pm.register_mold("TEST-006", material="P20")
        for t in ("2026-04-15T00:00:00+00:00",
                  "2026-05-01T00:00:00+00:00",
                  "2026-05-15T00:00:00+00:00"):
            pm.append_event(pm.PMEvent(mold_id="TEST-006", timestamp=t, action="clean"))
        in_may = pm.events_in_range("TEST-006",
                                     start="2026-05-01T00:00:00+00:00",
                                     end="2026-05-31T00:00:00+00:00")
        check("range: 2 in May (plus register at now if today is May)",
              sum(1 for e in in_may if e.action == "clean") == 2)


def t_list_molds_empty():
    with tempfile.TemporaryDirectory() as td:
        pm.PM_LOG_DIR = Path(td)
        check("list: empty when no events", pm.list_molds() == [])
        pm.register_mold("Z-99", material="X")
        check("list: 1 after register", pm.list_molds() == ["Z-99"])


def main() -> int:
    for fn in (
        t_register_and_load,
        t_append_multiple,
        t_status_for,
        t_shots_between_pm,
        t_defect_breakdown,
        t_events_in_range,
        t_list_molds_empty,
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
