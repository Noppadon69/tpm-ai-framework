"""
tpm_tools - runtime tool registry (Phase 3 Day 5)
ref: MASTER_PLAN_v6.md Section 13

Indirection layer so workers and external tools (MCP servers, plugins) can
be swapped at runtime without orchestrator code changes.
"""
from tpm_tools.registry import (
    ToolEntry,
    ToolRegistry,
    default_registry,
    get_for_action,
    list_tools,
)

__all__ = [
    "ToolEntry",
    "ToolRegistry",
    "default_registry",
    "get_for_action",
    "list_tools",
]
