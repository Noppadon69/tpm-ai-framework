"""
tpm_workers.base - common types for workers
ref: MASTER_PLAN_v5.md § 11
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WorkerType(str, Enum):
    REPORT = "report"
    EXCEL = "excel"
    PPTX = "pptx"
    VISION = "vision"
    CALC = "calc"
    VIBRATION = "vibration"


class WorkerStep(BaseModel):
    """One step inside a worker subgraph (Researcher / Writer / Analyst / etc.)"""
    name: str
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: Optional[datetime] = None
    success: bool = True
    output: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    notes: list[str] = Field(default_factory=list)

    def latency_ms(self) -> Optional[int]:
        if self.finished_at is None:
            return None
        return int((self.finished_at - self.started_at).total_seconds() * 1000)

    def finish(self, success: bool = True, error: str = "") -> None:
        self.finished_at = _utcnow()
        self.success = success
        if error:
            self.error = error
            self.success = False


class WorkerInput(BaseModel):
    """Input contract for any worker."""
    worker_type: WorkerType
    session_id: str
    user_request: str
    intent: dict[str, Any] = Field(default_factory=dict)
    target_subject: str = ""              # e.g., "SHIBAURA-EC100SX"
    time_range_days: int = 90             # last N days for analysis
    output_dir: Path = Path("output")
    extras: dict[str, Any] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}


class WorkerResult(BaseModel):
    """Output contract from any worker."""
    worker_type: WorkerType
    success: bool = False
    output_files: list[str] = Field(default_factory=list)
    summary: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    steps: list[WorkerStep] = Field(default_factory=list)
    auditor_passed: bool = False
    auditor_findings: list[str] = Field(default_factory=list)
    confidence: float = 0.0

    def add_step(self, step: WorkerStep) -> None:
        self.steps.append(step)

    def total_latency_ms(self) -> int:
        return sum(s.latency_ms() or 0 for s in self.steps)
