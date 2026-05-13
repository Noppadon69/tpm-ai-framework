#!/usr/bin/env python
"""
scripts/pm_dashboard.py - PM dashboard renderer (Section 25.2.5)

Renders a 2x2 matplotlib dashboard for one mold:
  [1] cumulative shot count over time
  [2] PM event timeline (clean / repair / defect bars)
  [3] shots between consecutive PM events (gauge: were we hitting interval?)
  [4] defect breakdown bar chart

Output: output/mold_dashboards/<mold_id>_<YYYY-MM-DD>.png

Designed to run with synthetic pre-internship data (`scripts/log_pm.py
register/clean/...`) - on Day 1 of internship, intern just keeps logging
real events and the dashboard regenerates against real history.

Usage:
    python scripts/pm_dashboard.py M-101
    python scripts/pm_dashboard.py --all          # render every registered mold
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import os
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.dates import DateFormatter  # noqa: E402

from tpm_mold.pm_log import (  # noqa: E402
    PMAction,
    defect_breakdown,
    list_molds,
    load_events,
    shots_between_pm,
    status_for,
)

OUT_DIR = REPO / "output" / "mold_dashboards"


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def render_mold_dashboard(mold_id: str) -> Path | None:
    events = load_events(mold_id)
    if not events:
        print(f"[skip] {mold_id}: no events logged")
        return None

    status = status_for(mold_id)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(
        f"PM Dashboard - {mold_id}"
        + (f" ({status.material})" if status and status.material else "")
        + f"  |  shots={status.cumulative_shots:,}, events={status.n_events}",
        fontsize=14,
    )

    # ---- [1,1] cumulative shot count over time ----
    ax = axes[0][0]
    xs, ys = [], []
    for e in events:
        if e.shot_count is not None:
            xs.append(_parse_iso(e.timestamp))
            ys.append(e.shot_count)
    if xs:
        ax.plot(xs, ys, marker="o", color="#1f77b4")
        ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))
    ax.set_title("Cumulative shot count")
    ax.set_xlabel("date")
    ax.set_ylabel("shots")
    ax.grid(True, alpha=0.3)

    # ---- [1,2] event timeline (color-coded actions) ----
    ax = axes[0][1]
    color_map = {
        PMAction.REGISTER.value: "#888",
        PMAction.INSPECT.value: "#7fbf7f",
        PMAction.CLEAN.value: "#1f77b4",
        PMAction.LUBRICATE.value: "#17becf",
        PMAction.REPAIR.value: "#ff7f0e",
        PMAction.OVERHAUL.value: "#d62728",
        PMAction.DEFECT.value: "#e377c2",
        PMAction.SHOT_COUNT.value: "#aaa",
        PMAction.NOTE.value: "#bbb",
    }
    seen_actions: dict[str, bool] = {}
    for e in events:
        c = color_map.get(e.action, "#666")
        label = e.action if e.action not in seen_actions else None
        ax.scatter(
            _parse_iso(e.timestamp), e.action,
            color=c, s=60, label=label, zorder=3,
        )
        seen_actions[e.action] = True
    ax.set_title("Event timeline")
    ax.set_xlabel("date")
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(True, axis="x", alpha=0.3)
    ax.xaxis.set_major_formatter(DateFormatter("%m/%d"))

    # ---- [2,1] shots between consecutive PM events ----
    ax = axes[1][0]
    deltas = shots_between_pm(mold_id)
    if deltas:
        bars = ax.bar(range(1, len(deltas) + 1), deltas, color="#2ca02c", alpha=0.8)
        ax.set_xticks(range(1, len(deltas) + 1))
        mean_delta = sum(deltas) / len(deltas)
        ax.axhline(mean_delta, color="red", linestyle="--", linewidth=1, label=f"mean = {mean_delta:,.0f}")
        ax.legend(fontsize=9)
        # Annotate each bar with its value
        for b, d in zip(bars, deltas):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                    f"{d:,}", ha="center", va="bottom", fontsize=8)
    else:
        ax.text(0.5, 0.5, "Not enough PM events yet\n(need >= 2 to compute deltas)",
                ha="center", va="center", transform=ax.transAxes, fontsize=10)
    ax.set_title("Shots between PM events")
    ax.set_xlabel("PM interval #")
    ax.set_ylabel("shots since last PM")
    ax.grid(True, axis="y", alpha=0.3)

    # ---- [2,2] defect breakdown ----
    ax = axes[1][1]
    db = defect_breakdown(mold_id)
    if db:
        items = sorted(db.items(), key=lambda kv: kv[1], reverse=True)
        labels = [k for k, _ in items]
        counts = [v for _, v in items]
        bars = ax.barh(labels, counts, color="#e377c2", alpha=0.8)
        for b, c in zip(bars, counts):
            ax.text(b.get_width(), b.get_y() + b.get_height() / 2,
                    f" {c}", va="center", fontsize=9)
    else:
        ax.text(0.5, 0.5, "No defects logged",
                ha="center", va="center", transform=ax.transAxes, fontsize=10)
    ax.set_title("Defect breakdown")
    ax.set_xlabel("count")

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = mold_id.replace("/", "_").replace("\\", "_")
    out_path = OUT_DIR / f"{safe}_{datetime.now().strftime('%Y-%m-%d')}.png"
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] {mold_id} -> {out_path.relative_to(REPO)}")
    return out_path


def main() -> int:
    p = argparse.ArgumentParser(description="Render PM dashboard for one or all molds.")
    p.add_argument("mold_id", nargs="?", help="mold id (e.g. M-101)")
    p.add_argument("--all", action="store_true", help="render every registered mold")
    args = p.parse_args()

    if args.all:
        ids = list_molds()
        if not ids:
            print("(no molds registered yet - use scripts/log_pm.py)")
            return 0
        rc = 0
        for mid in ids:
            if not render_mold_dashboard(mid):
                rc = 1
        return rc

    if not args.mold_id:
        p.error("mold_id required (or pass --all)")

    return 0 if render_mold_dashboard(args.mold_id) else 2


if __name__ == "__main__":
    raise SystemExit(main())
