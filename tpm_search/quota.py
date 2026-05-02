"""
tpm_search.quota — track free-tier usage per provider
ref: MASTER_PLAN_v5.md § 6.4 + § 23.2 R7

Stores monthly counters in JSON file:
    .tpm_context/quota_search.json

Quotas (May 2026):
    tavily: 1,000 / month
    exa:    1,000 / month
    others: unlimited
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tpm_search.types import SearchProvider

REPO_ROOT = Path(__file__).resolve().parent.parent
QUOTA_FILE = REPO_ROOT / ".tpm_context" / "quota_search.json"

# Free-tier monthly limits (None = unlimited)
QUOTAS: dict[SearchProvider, Optional[int]] = {
    SearchProvider.SEARXNG: None,
    SearchProvider.DUCKDUCKGO: None,
    SearchProvider.WIKIPEDIA: None,
    SearchProvider.JINA: None,
    SearchProvider.TAVILY: 1000,
    SearchProvider.EXA: 1000,
}

# Soft-limit threshold — start warning when 90% used
SOFT_LIMIT_PCT = 0.90

_lock = threading.Lock()


def _now_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load() -> dict:
    if not QUOTA_FILE.exists():
        return {"month": _now_month(), "counts": {}}
    try:
        data = json.loads(QUOTA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"month": _now_month(), "counts": {}}
    # Reset on month rollover
    if data.get("month") != _now_month():
        return {"month": _now_month(), "counts": {}}
    return data


def _save(data: dict) -> None:
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def increment(provider: SearchProvider, amount: int = 1) -> int:
    """Bump usage and return new count."""
    with _lock:
        data = _load()
        cur = data["counts"].get(provider.value, 0) + amount
        data["counts"][provider.value] = cur
        _save(data)
        return cur


def remaining(provider: SearchProvider) -> Optional[int]:
    """Returns remaining requests, or None if unlimited."""
    limit = QUOTAS.get(provider)
    if limit is None:
        return None
    data = _load()
    used = data["counts"].get(provider.value, 0)
    return max(0, limit - used)


def is_available(provider: SearchProvider) -> bool:
    rem = remaining(provider)
    return rem is None or rem > 0


def is_soft_limited(provider: SearchProvider) -> bool:
    """Returns True when >= SOFT_LIMIT_PCT of quota used."""
    limit = QUOTAS.get(provider)
    if limit is None:
        return False
    rem = remaining(provider) or 0
    used_pct = 1 - (rem / limit)
    return used_pct >= SOFT_LIMIT_PCT


def status() -> dict[str, dict]:
    """Snapshot of all providers — for health_check / dashboard."""
    data = _load()
    out = {}
    for p, limit in QUOTAS.items():
        used = data["counts"].get(p.value, 0)
        rem = (limit - used) if limit is not None else None
        out[p.value] = {
            "limit": limit,
            "used": used,
            "remaining": rem,
            "soft_limited": is_soft_limited(p),
            "month": data["month"],
        }
    return out


if __name__ == "__main__":
    import json as _j
    print(_j.dumps(status(), ensure_ascii=False, indent=2))
