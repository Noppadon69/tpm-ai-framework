"""
generate_dummy_data.py - sample TPM data for pre-internship testing
ALL files prefixed DUMMY_ and placed in raw_data/_dummy/ for easy purge

Purge command:
    rm -rf raw_data/_dummy/   (Linux/WSL)
    Remove-Item -Recurse -Force raw_data\\_dummy\\   (PowerShell)

ref: MASTER_PLAN_v5.md - dummy data strategy
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

DUMMY_ROOT = Path("raw_data/_dummy")
np.random.seed(42)

# ============================================================
# Equipment registry - each has OWN typical issues + parts
# ============================================================
EQUIPMENT = {
    "SHIBAURA-EC100SX": {
        "type": "Injection Molding",
        "criticality": "A",
        "typical_issues": [
            ("Barrel temperature unstable",       "Mechanical", "High"),
            ("Injection pressure drop",           "Hydraulic",  "High"),
            ("Tie bar wear detected",             "Mechanical", "Medium"),
            ("Mold clamp force inconsistent",     "Mechanical", "High"),
            ("Heater band element burnt",         "Electrical", "Medium"),
        ],
        "common_parts": ["Heater band 220V/2kW", "Hydraulic O-ring kit", "Thermocouple K-type"],
    },
    "SHIBAURA-EC350SX": {
        "type": "Injection Molding",
        "criticality": "A",
        "typical_issues": [
            ("Hopper feed jam",                   "Mechanical", "Low"),
            ("Servo motor overheating axis Z",    "Electrical", "High"),
            ("Pressure sensor drift",             "Electrical", "Medium"),
            ("Cooling water flow restricted",     "Hydraulic",  "Medium"),
        ],
        "common_parts": ["Servo motor encoder", "Pressure transducer 0-200bar"],
    },
    "MAKINO-a51nx": {
        "type": "CNC Machining Center",
        "criticality": "B",
        "typical_issues": [
            ("Spindle bearing noise",             "Mechanical", "High"),
            ("Spindle coolant pump weak",         "Hydraulic",  "Medium"),
            ("X-axis backlash out of spec",       "Mechanical", "Medium"),
            ("ATC tool change misalignment",      "Mechanical", "High"),
            ("Servo motor X-axis overheating",    "Electrical", "High"),
        ],
        "common_parts": ["Spindle bearing NSK 7014", "Linear scale Heidenhain"],
    },
    "SODICK-AD35L": {
        "type": "Wire EDM",
        "criticality": "B",
        "typical_issues": [
            ("Wire breakage frequent",            "Mechanical", "High"),
            ("Dielectric tank contaminated",      "Hydraulic",  "Medium"),
            ("Wire tension sensor faulty",        "Electrical", "Medium"),
            ("Generator power fluctuation",       "Electrical", "High"),
        ],
        "common_parts": ["Brass wire 0.25mm 5kg spool", "Dielectric filter cartridge"],
    },
}

TECHNICIANS = ["Tanaka", "Suzuki", "Yamamoto", "Watanabe"]
STATUS_DIST = (
    ["Closed"] * 35 + ["Closed"] * 8 + ["In-Progress"] * 4
    + ["Waiting-Parts"] * 2 + ["Open"] * 1
)


# ============================================================
# Generate CM History
# ============================================================
def gen_cm_history(n_rows: int = 80) -> pd.DataFrame:
    rows = []
    machines = list(EQUIPMENT.keys())
    for i in range(n_rows):
        eq_name = np.random.choice(machines)
        eq = EQUIPMENT[eq_name]
        issue, category, severity = eq["typical_issues"][
            np.random.randint(len(eq["typical_issues"]))
        ]
        date = datetime(2026, 1, 1) + timedelta(days=int(np.random.randint(0, 120)))
        downtime = int(np.random.randint(45, 480))
        mttr = int(downtime * np.random.uniform(0.6, 0.9))
        labor_cost = mttr / 60 * 800
        parts_cost = int(np.random.choice(
            [0, 1500, 3500, 8000, 25000],
            p=[0.3, 0.25, 0.2, 0.15, 0.1],
        ))
        rows.append({
            "Event_ID": f"CM-2026-{i+1:04d}",
            "Date": date.strftime("%Y-%m-%d"),
            "Machine_Tag": eq_name,
            "Equipment_Type": eq["type"],
            "Criticality": eq["criticality"],
            "Problem_Reported": issue,
            "Category": category,
            "Severity": severity,
            "Status": np.random.choice(STATUS_DIST),
            "Downtime_Minutes": downtime,
            "MTTR_Minutes": mttr,
            "Technician": np.random.choice(TECHNICIANS),
            "Action_Taken": f"[DUMMY] Inspected, replaced parts, tested {issue.lower()}",
            "Root_Cause": "[DUMMY] Wear / fatigue / contamination",
            "Parts_Used": np.random.choice(eq["common_parts"]),
            "Labor_Cost_THB": round(labor_cost, 2),
            "Parts_Cost_THB": parts_cost,
            "Total_Cost_THB": round(labor_cost + parts_cost, 2),
        })
    return pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)


# ============================================================
# PM Schedule
# ============================================================
def gen_pm_schedule() -> pd.DataFrame:
    rows = []
    tasks_by_type = {
        "Injection Molding": [
            ("Tie bar lubrication + clearance check", "3M", 120, "LOTO required"),
            ("Heater band continuity test", "6M", 60, "Hot surface PPE"),
            ("Hydraulic oil sample analysis", "3M", 30, "None"),
        ],
        "CNC Machining Center": [
            ("Spindle oil change + filter", "3M", 90, "LOTO required"),
            ("Linear scale alignment check", "12M", 180, "Precision tools"),
            ("Way lubrication system check", "1M", 45, "None"),
        ],
        "Wire EDM": [
            ("Dielectric filter replacement", "1M", 60, "PPE for fluid handling"),
            ("Generator capacitor check", "6M", 90, "LOTO + HV warning"),
            ("Wire path alignment", "3M", 60, "None"),
        ],
    }
    for eq_name, eq in EQUIPMENT.items():
        for task, freq, duration, safety in tasks_by_type[eq["type"]]:
            rows.append({
                "Equipment": eq_name,
                "Equipment_Type": eq["type"],
                "Criticality": eq["criticality"],
                "Task": task,
                "Frequency": freq,
                "Estimated_Duration_Min": duration,
                "Safety_Requirements": safety,
                "Last_PM": "2026-03-15",
                "Next_Due": "2026-06-15",
                "Status": "Scheduled",
            })
    return pd.DataFrame(rows)


# ============================================================
# FMEA reference
# ============================================================
def gen_fmea() -> pd.DataFrame:
    rows = []
    fmea_id = 1
    for eq_name, eq in EQUIPMENT.items():
        for issue, category, severity in eq["typical_issues"]:
            sev = {"Low": 3, "Medium": 6, "High": 8, "Critical": 10}[severity]
            occ = int(np.random.randint(2, 8))
            det = int(np.random.randint(2, 8))
            rpn = sev * occ * det
            rows.append({
                "FMEA_ID": f"FMEA-{fmea_id:04d}",
                "Equipment": eq_name,
                "Function": "[DUMMY]",
                "Failure_Mode": issue,
                "Effect": "[DUMMY] Production loss + quality risk",
                "Cause": "[DUMMY] Wear / contamination / fatigue",
                "Severity": sev,
                "Occurrence": occ,
                "Detection": det,
                "RPN": rpn,
                "Recommended_Action": f"[DUMMY] Increase PM frequency for {issue}",
            })
            fmea_id += 1
    return pd.DataFrame(rows).sort_values("RPN", ascending=False).reset_index(drop=True)


# ============================================================
# LOTO procedures
# ============================================================
LOTO_TEXT = """---
classification: INTERNAL_DUMMY
status: dummy_for_pre_internship_testing
purge_when: real_internship_data_arrives
---

# DUMMY - LOTO Procedure: SHIBAURA-EC100SX (Injection Molding)

> WARNING: THIS IS DUMMY DATA - replace with real procedure on Day 1 of internship

## Pre-LOTO Verification
1. Notify operator + supervisor
2. Stop machine via main HMI Stop button
3. Wait for cycle complete

## Lockout Sequence
1. Turn main disconnect (red switch, side panel) to OFF position
2. Apply personal padlock + danger tag with name + date
3. Close hydraulic shutoff valve (V-201)
4. Apply lockout pin to mold clamp safety bar
5. Bleed hydraulic pressure via test point TP-3 (verify gauge reads 0 bar)

## Verification
1. Press start button - machine MUST NOT respond
2. Test heater bands cold - verify with thermal gun (< 50 deg C)

## Tagout Removal
- Reverse sequence
- Remove personal lock LAST (by lock owner only)

---

# DUMMY - LOTO Procedure: SODICK-AD35L (Wire EDM)

## Pre-LOTO
1. Power off via main panel
2. Drain dielectric tank (high voltage residual)

## Lockout
1. Lock main breaker (red, panel A)
2. Lock dielectric pump (panel B)
3. Lock generator capacitor discharge unit (HV warning)
4. Verify with multimeter > 60s after power-off

## Verification
1. HV warning lamp must be OFF
2. Capacitor voltage < 50V
"""


def gen_loto_procedures() -> str:
    return LOTO_TEXT


# ============================================================
# Equipment specs (markdown)
# ============================================================
def gen_equipment_specs() -> str:
    out = "# DUMMY - Equipment Reference Specs\n\n"
    out += "> All values are **placeholder** for system testing only.\n"
    out += "> Replace with real spec sheets on Day 1 of internship.\n\n"
    for name, eq in EQUIPMENT.items():
        out += f"## {name} ({eq['type']})\n\n"
        out += f"- Criticality: **{eq['criticality']}** (ABC class)\n"
        out += f"- Type: {eq['type']}\n"
        out += "- Typical issues:\n"
        for iss, cat, sev in eq['typical_issues']:
            out += f"  - {iss} ({cat}, severity={sev})\n"
        out += "- Common spare parts:\n"
        for p in eq['common_parts']:
            out += f"  - {p}\n"
        out += "\n"
    return out


# ============================================================
# README
# ============================================================
README_TEXT = """# raw_data/_dummy/ - Pre-internship Test Data

WARNING: ALL files in this folder are DUMMY - generated by `scripts/generate_dummy_data.py`

## Purpose
Test the TPM AI pipeline (OpenKB compile, ChromaDB index, Auditor, Night Cycle)
before real internship data arrives.

## Purge Strategy (Day 1 of internship)

```bash
# Linux/WSL
rm -rf raw_data/_dummy/

# PowerShell
Remove-Item -Recurse -Force raw_data\\_dummy\\

# Recompile wiki without dummy
python -m openkb compile --vault .tpm_context/wiki/ --rebuild

# Verify dummy purged
grep -r "DUMMY" .tpm_context/wiki/ && echo "WARN: dummy traces remain"
```

## Files
- DUMMY_CM_History_2026.xlsx - 80 corrective maintenance events (correlated)
- DUMMY_PM_Schedule_2026.xlsx - preventive maintenance plan
- DUMMY_FMEA_Reference.xlsx - failure mode template
- DUMMY_LOTO_Procedures.md - sample LOTO procedures
- DUMMY_Equipment_Specs.md - equipment reference

## Classification
All files tagged INTERNAL_DUMMY - should NEVER egress to L3 or cloud.
"""


def gen_readme() -> str:
    return README_TEXT


# ============================================================
# Main
# ============================================================
def main() -> int:
    DUMMY_ROOT.mkdir(parents=True, exist_ok=True)
    (DUMMY_ROOT / "excel_logs").mkdir(exist_ok=True)
    (DUMMY_ROOT / "pdf_manuals").mkdir(exist_ok=True)
    (DUMMY_ROOT / "standards").mkdir(exist_ok=True)

    cm = gen_cm_history()
    cm.to_excel(DUMMY_ROOT / "excel_logs" / "DUMMY_CM_History_2026.xlsx", index=False)
    print(f"[ok] CM history: {len(cm)} rows")

    pm = gen_pm_schedule()
    pm.to_excel(DUMMY_ROOT / "excel_logs" / "DUMMY_PM_Schedule_2026.xlsx", index=False)
    print(f"[ok] PM schedule: {len(pm)} tasks")

    fmea = gen_fmea()
    fmea.to_excel(DUMMY_ROOT / "excel_logs" / "DUMMY_FMEA_Reference.xlsx", index=False)
    print(f"[ok] FMEA: {len(fmea)} entries (top RPN={fmea.iloc[0]['RPN']})")

    (DUMMY_ROOT / "DUMMY_LOTO_Procedures.md").write_text(
        gen_loto_procedures(), encoding="utf-8"
    )
    print("[ok] LOTO procedures")

    (DUMMY_ROOT / "DUMMY_Equipment_Specs.md").write_text(
        gen_equipment_specs(), encoding="utf-8"
    )
    print("[ok] Equipment specs")

    (DUMMY_ROOT / "_DUMMY_README.md").write_text(gen_readme(), encoding="utf-8")
    print("[ok] README + purge instructions")

    print(f"\n[DONE] All dummy data in {DUMMY_ROOT}/")
    print("       Purge later with: rm -rf raw_data/_dummy/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
