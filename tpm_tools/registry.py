"""
tpm_tools.registry - load + resolve tools at runtime
ref: MASTER_PLAN_v6.md Section 13, Phase 3 Day 5

The registry is JSON at .tpm_context/tool_registry.json. Each entry binds
a logical action (lookup/report/calc/vision/...) to a Python entry point
and declares what it can do.

Resolution order:
  1. exact action match
  2. capability keyword in intent.scope
  3. fallback to a tool tagged is_fallback=True

Future MCP integration: an entry may declare protocol='mcp' instead of
'python', with a URL/socket. The current loader recognises 'mcp' entries
but does NOT dial them yet (skipped, logged as 'mcp-deferred'); they go
into the registry list so the catalog is complete.
"""
from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = REPO_ROOT / ".tpm_context" / "tool_registry.json"


@dataclass
class ToolEntry:
    """One tool in the registry."""
    id: str
    action: str                                # canonical intent action
    name: str
    module: str                                # 'tpm_workers.calc'
    entry_point: str                           # 'run_calc_worker'
    version: str = "0.0.0"
    capabilities: list[str] = field(default_factory=list)
    classification_allowed: list[str] = field(default_factory=lambda: ["PUBLIC", "INTERNAL"])
    protocol: str = "python"                   # 'python' | 'mcp'
    priority: int = 0                          # higher wins ties
    is_fallback: bool = False
    notes: str = ""

    @property
    def fq_callable(self) -> str:
        return f"{self.module}.{self.entry_point}"

    def resolve(self) -> Callable[..., Any]:
        """Import the module + return the entry-point callable."""
        if self.protocol != "python":
            raise RuntimeError(
                f"tool {self.id!r} uses protocol={self.protocol!r}; not yet supported"
            )
        mod = importlib.import_module(self.module)
        fn = getattr(mod, self.entry_point, None)
        if fn is None or not callable(fn):
            raise AttributeError(
                f"tool {self.id!r}: {self.fq_callable} not callable"
            )
        return fn


class ToolRegistry:
    """In-memory registry built from the JSON file."""

    def __init__(self, entries: Optional[list[ToolEntry]] = None):
        self.entries: list[ToolEntry] = list(entries or [])

    # ---- loading ----
    @classmethod
    def from_file(cls, path: Path | str = DEFAULT_REGISTRY_PATH) -> "ToolRegistry":
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            log.error("registry: malformed JSON at %s: %s", path, e)
            return cls()
        raw_entries = data.get("tools") or []
        entries: list[ToolEntry] = []
        for raw in raw_entries:
            try:
                entries.append(ToolEntry(**raw))
            except TypeError as e:
                log.warning("registry: skipping malformed entry %r: %s", raw.get("id"), e)
        return cls(entries)

    # ---- queries ----
    def get(self, tool_id: str) -> Optional[ToolEntry]:
        for e in self.entries:
            if e.id == tool_id:
                return e
        return None

    def list_actions(self) -> list[str]:
        seen: list[str] = []
        for e in self.entries:
            if e.action not in seen:
                seen.append(e.action)
        return seen

    def get_for_action(
        self,
        action: str,
        *,
        classification: str = "INTERNAL",
        capabilities_hint: Optional[list[str]] = None,
    ) -> Optional[ToolEntry]:
        """
        Return the best tool for an action.

        Filters:
          - action matches (or any fallback if no exact match)
          - classification is in tool.classification_allowed
        Sort:
          - +1000 if action exact match
          - +100 per capability keyword match
          - + priority
        """
        candidates: list[tuple[int, ToolEntry]] = []
        for e in self.entries:
            if classification not in e.classification_allowed:
                continue
            score = 0
            if e.action == action:
                score += 1000
            elif e.is_fallback:
                score += 1
            else:
                continue
            if capabilities_hint:
                for c in capabilities_hint:
                    if c.lower() in (k.lower() for k in e.capabilities):
                        score += 100
            score += e.priority
            candidates.append((score, e))

        if not candidates:
            return None
        candidates.sort(key=lambda t: t[0], reverse=True)
        return candidates[0][1]


# ============================================================
# Module-level convenience: a single default registry instance
# ============================================================
_DEFAULT: Optional[ToolRegistry] = None


def default_registry() -> ToolRegistry:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = ToolRegistry.from_file()
    return _DEFAULT


def get_for_action(action: str, **kw) -> Optional[ToolEntry]:
    return default_registry().get_for_action(action, **kw)


def list_tools() -> list[ToolEntry]:
    return list(default_registry().entries)


def reload() -> ToolRegistry:
    """Reset the cached default and reload from disk."""
    global _DEFAULT
    _DEFAULT = None
    return default_registry()
