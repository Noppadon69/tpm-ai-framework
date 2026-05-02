"""
tpm_search.egress — classification + sanitizer for L3 egress
ref: MASTER_PLAN_v5.md § 21.1, § 21.2

Two responsibilities:
  1. classify(query) → Classification (auto-tag query before egress)
  2. sanitize(text)  → strip PII / equipment tags before sending to cloud

Hard rule:
  CONFIDENTIAL → block external L3 entirely
  RESTRICTED   → block all external (and most internal log writes)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

import yaml

from tpm_search.types import Classification

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_FILE = REPO_ROOT / ".tpm_context" / "data_classification.yaml"

# Lazy-loaded policy
_policy: dict | None = None


def _load_policy() -> dict:
    global _policy
    if _policy is None:
        _policy = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    return _policy


# ============================================================
# Classification
# ============================================================
def classify(text: str) -> Classification:
    """
    Auto-classify text. Returns the *highest* (most restrictive) class found.
    Defaults to PUBLIC if no patterns match (be careful — see fallback rule below).
    """
    policy = _load_policy()
    auto = policy.get("auto_classify_patterns", {})

    # Check in order of restrictiveness
    for level in (Classification.RESTRICTED, Classification.CONFIDENTIAL,
                  Classification.INTERNAL):
        rules = auto.get(level.value, {}) or {}
        # Keyword match
        for kw in rules.get("keywords", []) or []:
            if kw.lower() in text.lower():
                return level
        # Regex match
        for pattern_def in rules.get("regex_patterns", []) or []:
            if isinstance(pattern_def, dict):
                pattern = pattern_def.get("pattern", "")
                flags = 0 if pattern_def.get("case_sensitive", False) else re.IGNORECASE
            else:
                pattern, flags = pattern_def, re.IGNORECASE
            if pattern and re.search(pattern, text, flags):
                return level
        # File-pattern (informational, not used for query text)

    # INTERNAL fallback — if classification rules say "INTERNAL is default"
    internal_rules = auto.get("INTERNAL", {}) or {}
    if internal_rules.get("fallback", False):
        # only if explicitly opted-in; otherwise PUBLIC
        return Classification.INTERNAL

    return Classification.PUBLIC


# ============================================================
# Egress check (raises if blocked)
# ============================================================
class EgressBlocked(Exception):
    """Raised when content classification forbids external egress."""
    pass


def check_egress(
    text: str,
    destination: str,
    classification: Classification | None = None,
) -> Classification:
    """
    Verify content can leave to `destination`. Raises EgressBlocked otherwise.
    Returns the classification used.

    Destination strings: "L3_search", "cloud_fallback", "github_public",
                         "github_private", "external_email", ...
    """
    policy = _load_policy()
    classes = policy.get("classifications", {})

    cls = classification or classify(text)
    rules = classes.get(cls.value, {})

    allowed = rules.get("egress_allowed", []) or []
    forbidden = rules.get("forbidden", []) or []

    if destination in forbidden:
        raise EgressBlocked(
            f"{cls.value} forbids egress to {destination!r}. "
            f"Allowed: {allowed}"
        )
    if allowed and destination not in allowed:
        raise EgressBlocked(
            f"{cls.value} does not allow egress to {destination!r}. "
            f"Allowed: {allowed}"
        )
    return cls


# ============================================================
# Sanitizer (for INTERNAL → cloud, see § 18.5)
# ============================================================
_SANITIZER_CACHE: list[tuple[str, str, str]] | None = None  # (name, pattern, replacement)


def _get_sanitizer_rules() -> list[tuple[str, str, str]]:
    global _SANITIZER_CACHE
    if _SANITIZER_CACHE is None:
        policy = _load_policy()
        rules = policy.get("sanitizer_rules", {}) or {}
        _SANITIZER_CACHE = [
            (name, r["pattern"], r["replace_with"])
            for name, r in rules.items()
            if "pattern" in r and "replace_with" in r
        ]
    return _SANITIZER_CACHE


def sanitize(text: str) -> Tuple[str, dict[str, str]]:
    """
    Replace PII/tags with placeholders. Returns (sanitized_text, replacements_map)
    so caller can desanitize the response if needed.
    """
    out = text
    replacements: dict[str, str] = {}
    for name, pattern, placeholder in _get_sanitizer_rules():
        idx = 0
        for match in re.finditer(pattern, out, re.IGNORECASE):
            original = match.group()
            if original not in replacements.values():
                key = f"{placeholder}_{idx}"
                replacements[key] = original
                idx += 1
        for key, original in list(replacements.items()):
            out = out.replace(original, key, 1)
    return out, replacements


def desanitize(text: str, replacements: dict[str, str]) -> str:
    out = text
    for key, original in replacements.items():
        out = out.replace(key, original)
    return out
