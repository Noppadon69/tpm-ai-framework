"""
tpm_core.llm - Ollama wrapper with retry + JSON mode
ref: MASTER_PLAN_v5.md § 4.2 (orchestrator), § 7.3 (structured prompt)

Uses ollama Python SDK; falls back to direct HTTP if unavailable.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx

log = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Default timeouts (seconds)
# First call may be slow due to cold-start (5GB model load, ~30-90s on RTX 5060).
DEFAULT_TIMEOUT = 180.0
DEFAULT_RETRIES = 2


# ============================================================
# Low-level call (HTTP, no SDK dependency)
# ============================================================
def _http_chat(
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    format: str | dict | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    if format is not None:
        payload["format"] = format

    with httpx.Client(timeout=timeout) as client:
        r = client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()


# ============================================================
# Public API
# ============================================================
def chat(
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    json_mode: bool = False,
    json_schema: dict | None = None,
    retries: int = DEFAULT_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """
    Send chat messages, return assistant text content.

    json_mode=True forces Ollama to emit valid JSON (uses 'format' field).
    json_schema = use Ollama 0.5+ structured output (preferred when supported).
    """
    fmt: str | dict | None = None
    if json_schema is not None:
        fmt = json_schema  # Ollama supports JSON schema as format
    elif json_mode:
        fmt = "json"

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            t0 = time.perf_counter()
            resp = _http_chat(
                model, messages, temperature=temperature, format=fmt, timeout=timeout
            )
            dt = int((time.perf_counter() - t0) * 1000)
            content = resp.get("message", {}).get("content", "")
            log.debug("ollama %s in %dms: %s", model, dt, content[:80])
            return content
        except Exception as e:  # noqa: BLE001
            last_error = e
            log.warning("ollama attempt %d failed: %s", attempt + 1, e)
            time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"ollama chat failed after {retries+1} attempts: {last_error}")


def chat_json(
    model: str,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.1,
    json_schema: dict | None = None,
    retries: int = DEFAULT_RETRIES,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    Convenience wrapper: sends with JSON mode + parses response.
    Raises ValueError on parse failure after all retries.
    """
    last_text = ""
    for attempt in range(retries + 1):
        last_text = chat(
            model,
            messages,
            temperature=temperature,
            json_mode=json_schema is None,
            json_schema=json_schema,
            retries=0,
            timeout=timeout,
        )
        try:
            return json.loads(last_text)
        except json.JSONDecodeError as e:
            log.warning("json parse failed on attempt %d: %s", attempt + 1, e)
            # try to extract first {...} block
            stripped = _try_extract_json(last_text)
            if stripped is not None:
                return stripped
    raise ValueError(f"chat_json: invalid JSON after {retries+1} retries: {last_text[:200]!r}")


def _try_extract_json(text: str) -> dict | None:
    """Best-effort: find the first balanced {...} block."""
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


# ============================================================
# Health check (used by orchestrator startup)
# ============================================================
def health() -> bool:
    try:
        with httpx.Client(timeout=3.0) as c:
            r = c.get(f"{OLLAMA_HOST}/api/tags")
            return r.status_code == 200
    except Exception:
        return False
