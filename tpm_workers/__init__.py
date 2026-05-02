"""
tpm_workers - role-based worker subgraphs (Phase 3)
ref: MASTER_PLAN_v5.md § 11

Phase 3 Day 1 scope:
    Report Worker  (Researcher -> Writer -> Reviewer -> .docx)
    Excel Worker   (Researcher -> Analyst -> Coder -> Reviewer -> .xlsx)

Future workers (Day 2-5):
    PPTX Worker    (slide content + python-pptx)
    Vision Worker  (Qwen2.5-VL + crack detection)
    Calc Worker    (SymPy + Hybrid Debate for high-stakes)
"""
from tpm_workers.base import (
    WorkerInput,
    WorkerResult,
    WorkerStep,
    WorkerType,
)
from tpm_workers.report import run_report_worker
from tpm_workers.excel import run_excel_worker

__all__ = [
    "WorkerInput",
    "WorkerResult",
    "WorkerStep",
    "WorkerType",
    "run_report_worker",
    "run_excel_worker",
]

__version__ = "0.1.0"
