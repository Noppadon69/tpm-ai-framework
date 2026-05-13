"""
telegram_bridge.py - Telegram polling bridge for TPM AI.

Reads TPM_TELEGRAM_BOT_TOKEN from .env, polls Telegram for messages, and
either dispatches a built-in command (fast path) or forwards plain text
to scripts/cli_demo.py (LLM path).

Security: ALLOWLIST gate. Without TPM_TELEGRAM_ALLOWED_USERS set,
non-whitelisted users get only /me and /help (so the owner can discover
their own chat_id and add it to .env, then restart).

Why exist when services/n8n/ scaffold also targets Telegram:
  n8n needs UI clicks to attach a credential to a workflow; can't run
  end-to-end autonomously. This gives a working bot in code today. If you
  outgrow it (multi-workflow, cron, file watcher), migrate to n8n per the
  decision gate in services/n8n/README.md.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import httpx

# Avast / corporate proxies inject MITM certs that aren't in certifi.
# truststore.inject_into_ssl() makes Python use the Windows cert store
# which DOES have those intermediates. Safe no-op on Linux/Mac.
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:  # noqa: BLE001
    pass


# ---------------------------------------------------------------------------
# Paths (resilient to running from a worktree)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent


def _find_venv_python(start: Path) -> Path:
    for parent in [start, *start.parents]:
        cand = parent / ".venv" / "Scripts" / "python.exe"
        if cand.is_file():
            return cand
    return start / ".venv" / "Scripts" / "python.exe"


def _find_env(start: Path) -> Path:
    for parent in [start, *start.parents]:
        cand = parent / ".env"
        if cand.is_file():
            return cand
    return start / ".env"


ENV_PATH = _find_env(REPO_ROOT)
PY = _find_venv_python(REPO_ROOT)
MAIN_CHECKOUT = PY.parent.parent.parent  # python.exe -> Scripts -> .venv -> root
SCRIPTS = MAIN_CHECKOUT / "scripts"
CLI = SCRIPTS / "cli_demo.py"

POLL_TIMEOUT_S = 25
HTTP_TIMEOUT_S = 35
CLI_TIMEOUT_S = 180
FAST_CMD_TIMEOUT_S = 30  # for /defect, /pm status, etc. (no LLM)


# ---------------------------------------------------------------------------
# Env loader + allowlist
# ---------------------------------------------------------------------------
def _load_env(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _parse_allowlist(env_val: str) -> set[int]:
    out: set[int] = set()
    for tok in env_val.replace(";", ",").split(","):
        tok = tok.strip()
        if tok.isdigit():
            out.add(int(tok))
    return out


# ---------------------------------------------------------------------------
# Telegram I/O helpers
# ---------------------------------------------------------------------------
def _send_typing(api: str, chat_id: int) -> None:
    try:
        httpx.post(
            f"{api}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
            timeout=5.0,
        )
    except Exception:  # noqa: BLE001
        pass


def _send_message(api: str, chat_id: int, text: str) -> None:
    text = text or "(empty)"
    for i in range(0, len(text), 4000):
        chunk = text[i : i + 4000]
        try:
            r = httpx.post(
                f"{api}/sendMessage",
                json={"chat_id": chat_id, "text": chunk},
                timeout=15.0,
            )
            if r.status_code != 200:
                logging.warning("sendMessage HTTP %d: %s", r.status_code, r.text[:200])
        except Exception as e:  # noqa: BLE001
            logging.error("sendMessage failed: %s", e)


def _set_my_commands(api: str, commands: Iterable[tuple[str, str]]) -> None:
    payload = {"commands": [{"command": c, "description": d} for c, d in commands]}
    try:
        r = httpx.post(f"{api}/setMyCommands", json=payload, timeout=10.0)
        if r.status_code != 200:
            logging.warning("setMyCommands HTTP %d: %s", r.status_code, r.text[:200])
        else:
            logging.info("registered %d commands with Telegram", len(payload["commands"]))
    except Exception as e:  # noqa: BLE001
        logging.warning("setMyCommands failed: %s", e)


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------
def _run_py(args: list[str], timeout_s: int) -> str:
    if not PY.is_file():
        return f"[bridge error] venv python not found at {PY}"
    try:
        proc = subprocess.run(
            [str(PY), *args],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=str(MAIN_CHECKOUT),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        out = (proc.stdout or "").strip()
        if not out:
            err = (proc.stderr or "").strip()
            return f"[empty stdout, rc={proc.returncode}]\n{err[-1500:]}"
        return out
    except subprocess.TimeoutExpired:
        return f"[timeout {timeout_s}s]"
    except Exception as e:  # noqa: BLE001
        return f"[exception] {type(e).__name__}: {e}"


_SESSION_RE = re.compile(r"session=([0-9a-f]{8,})")


_CITATION_RE = re.compile(r"\[(\d+)\]")
# Strip any "Sources:" / "*Sources:*" / "**Sources:**" footer the LLM appended
# (inline bare-number form OR multi-line "[N] <url>" form) and everything
# after it. We replace it with our own rendering from search.top_results.
_SOURCES_FOOTER_RE = re.compile(
    r"\n*\s*\**\s*sources?\s*:?\**.*\Z",
    re.IGNORECASE | re.DOTALL,
)


def _render_sources_list(search: dict | None, answer: str) -> str:
    """
    Build a readable 'Sources:' footer mapping [N] markers in `answer` to the
    real result title + URL from search.top_results. Falls back to all_titles
    (no URLs) when working against older session JSONs.
    """
    if not search:
        return ""
    top = search.get("top_results") or []
    if not top:
        # legacy session JSON shape - titles only
        titles = search.get("all_titles") or []
        if not titles:
            return ""
        cited = sorted({int(n) for n in _CITATION_RE.findall(answer)})
        # if no explicit citation markers, show top 3 anyway
        idxs = cited if cited else list(range(1, min(4, len(titles) + 1)))
        lines = ["Sources:"]
        for i in idxs:
            if 1 <= i <= len(titles):
                lines.append(f"[{i}] {titles[i-1]}")
        return "\n".join(lines)

    cited = sorted({int(n) for n in _CITATION_RE.findall(answer)})
    if not cited:
        # show the first 3 anyway so the user has something to follow
        cited = list(range(1, min(4, len(top) + 1)))
    lines = ["Sources:"]
    for i in cited:
        if 1 <= i <= len(top):
            r = top[i - 1]
            title = (r.get("title") or "").strip() or "(untitled)"
            url = (r.get("url") or "").strip()
            lines.append(f"[{i}] {title}")
            if url:
                lines.append(f"    {url}")
    return "\n".join(lines)


def _format_orchestrator_result(data: dict) -> str:
    """
    Pretty-format what the orchestrator wrote to its session JSON.

    Prefer final_output.answer (lookup / search synthesis) + expand the
    LLM's bare-bones "[1] [2] [3]" sources footer into a readable list of
    title + URL using search.top_results. Otherwise look for worker-
    specific summaries. Last resort: surface the error.
    """
    fo = data.get("final_output") or {}
    intent = data.get("intent") or {}
    action = intent.get("action") or ""

    # Direct answer from lookup/search/synthesis pipeline
    ans = fo.get("answer")
    if isinstance(ans, str) and ans.strip():
        body = ans.strip()
        # Strip the LLM's footer like "**Sources:** [1], [2], [3]" - we'll
        # replace it with a real list using search.top_results below.
        stripped = _SOURCES_FOOTER_RE.sub("", body).rstrip()
        sources = _render_sources_list(fo.get("search"), body)
        if sources:
            return f"{stripped}\n\n{sources}"
        return stripped

    # Worker outputs land under final_output too in some shapes
    for key in ("summary", "result", "text", "output"):
        v = fo.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()

    # Worker-specific structured outputs
    if action == "calc":
        calc = fo.get("calc") or {}
        if calc.get("pretty"):
            return calc["pretty"]
    if action == "vision":
        vis = fo.get("vision") or {}
        desc = vis.get("description") or ""
        defs = vis.get("defects") or []
        if desc or defs:
            return f"{desc}\n\nDefects: {', '.join(defs) if defs else '(none)'}".strip()

    # Error pathway
    err = data.get("error")
    if err:
        return f"[orchestrator error] {err}"

    # Diagnostic fallback (still readable)
    return (
        f"[no answer field in session JSON]\n"
        f"phase={data.get('final_phase')} action={action} "
        f"subject={intent.get('subject', '')} "
        f"duration={data.get('duration_ms', 0)}ms"
    )


def _find_session_json(session_id: str) -> Path | None:
    """Look in today's and yesterday's daily dirs (cheap, covers midnight)."""
    base = MAIN_CHECKOUT / ".tpm_context" / "decision_log" / "daily"
    today = datetime.now()
    for offset in (0, -1):
        d = (today + timedelta(days=offset)).strftime("%Y-%m-%d")
        cand = base / d / f"{session_id}.json"
        if cand.is_file():
            return cand
    return None


def _call_cli(prompt: str) -> str:
    """
    Run cli_demo, then read the session JSON to surface the actual synthesised
    answer instead of the orchestrator's stdout/stderr console noise. cli_demo
    prints session metadata (phase/intent/handoff count) to stdout but NOT the
    answer itself - the answer lives in the auto-persisted decision_log JSON.
    """
    if not CLI.is_file():
        return f"[bridge error] cli_demo.py not found at {CLI}"
    if not PY.is_file():
        return f"[bridge error] venv python not found at {PY}"
    try:
        proc = subprocess.run(
            [str(PY), str(CLI), prompt],
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_S,
            cwd=str(MAIN_CHECKOUT),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except subprocess.TimeoutExpired:
        return f"[cli timeout {CLI_TIMEOUT_S}s] try again or shorter prompt"
    except Exception as e:  # noqa: BLE001
        return f"[bridge exception] {type(e).__name__}: {e}"

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")

    # Find the session_id - orchestrator logs `[init] session=<sid> ...`
    m = _SESSION_RE.search(combined)
    if m:
        sid = m.group(1)
        path = _find_session_json(sid)
        if path is not None:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return _format_orchestrator_result(data)
            except Exception as e:  # noqa: BLE001
                logging.warning("session JSON parse failed: %s", e)

    # No session_id or no JSON yet - last-resort fallback
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if out:
        return out[-3500:]
    return f"[no answer; rc={proc.returncode}]\n{err[-1200:]}"


# ---------------------------------------------------------------------------
# Built-in commands
# ---------------------------------------------------------------------------
HELP_TEXT = (
    "TPM AI bot commands\n"
    "\n"
    "/me              your chat_id (paste into TPM_TELEGRAM_ALLOWED_USERS)\n"
    "/help            this help\n"
    "/status          ollama + bridge health check\n"
    "/defect <name>   mold defect lookup, e.g. /defect Flash\n"
    "/pm <mold_id>    PM status for a mold, e.g. /pm M-101\n"
    "/calc <expr>     quick SymPy calc, e.g. /calc 50000/2.5e-5\n"
    "(photo)          send a photo (with optional caption) -> Vision worker\n"
    "(plain text)     full orchestrator pipeline via cli_demo.py (LLM)\n"
)


def _cmd_me(chat_id: int, user: dict) -> str:
    return (
        f"chat_id: {chat_id}\n"
        f"username: @{user.get('username', '(none)')}\n"
        f"name: {user.get('first_name', '')} {user.get('last_name', '')}\n"
        f"\n"
        f"To authorize, add this line to {ENV_PATH}:\n"
        f"  TPM_TELEGRAM_ALLOWED_USERS={chat_id}\n"
        f"Then restart this bridge."
    )


def _cmd_status() -> str:
    # ollama health
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3.0)
        ollama_ok = r.status_code == 200
        models = [m.get("name") for m in r.json().get("models", [])][:5] if ollama_ok else []
    except Exception:  # noqa: BLE001
        ollama_ok = False
        models = []
    lines = [
        f"ollama: {'OK' if ollama_ok else 'DOWN'}",
        f"models: {', '.join(models) if models else '(none)'}",
        f"main checkout: {MAIN_CHECKOUT}",
        f"env: {ENV_PATH}  ({'exists' if ENV_PATH.is_file() else 'missing'})",
        f"cli_demo: {'present' if CLI.is_file() else 'missing'}",
    ]
    return "\n".join(lines)


def _cmd_defect(arg: str) -> str:
    if not arg.strip():
        return "usage: /defect <name>  (e.g. /defect Flash)"
    script = SCRIPTS / "lookup_defect.py"
    if not script.is_file():
        return f"[bridge error] {script.name} not found"
    return _run_py([str(script), arg], FAST_CMD_TIMEOUT_S)


def _cmd_pm(arg: str) -> str:
    if not arg.strip():
        return "usage: /pm <mold_id> [status|list|delta|breakdown]\n  e.g. /pm M-101 status"
    parts = shlex.split(arg)
    mold_id = parts[0]
    sub = parts[1] if len(parts) > 1 else "status"
    script = SCRIPTS / "log_pm.py"
    if not script.is_file():
        return f"[bridge error] {script.name} not found"
    return _run_py([str(script), mold_id, sub], FAST_CMD_TIMEOUT_S)


def _cmd_calc(arg: str) -> str:
    expr = arg.strip()
    if not expr:
        return "usage: /calc <expression>  (e.g. /calc 50000/2.5e-5)"
    # Pure SymPy numeric eval (no formula library lookup); safer than
    # invoking the full calc worker for a one-liner.
    safe_chars = set("0123456789.+-*/() eE_,piPI")
    if not all(c in safe_chars or c.isalpha() for c in expr):
        return "calc: only digits, operators, and simple identifiers allowed"
    try:
        import sympy
        val = sympy.sympify(expr).evalf()
        return f"{expr} = {val}"
    except Exception as e:  # noqa: BLE001
        return f"[calc error] {type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Photo handler (Telegram getFile + Vision worker)
# ---------------------------------------------------------------------------
TELEGRAM_PHOTOS_DIR = MAIN_CHECKOUT / "raw_data" / "telegram_photos"


def _download_telegram_file(api: str, token: str, file_id: str,
                            target_dir: Path) -> Path | None:
    """Resolve a Telegram file_id to a local Path."""
    try:
        r = httpx.get(f"{api}/getFile", params={"file_id": file_id}, timeout=10.0)
        r.raise_for_status()
        info = r.json().get("result", {})
        remote_path = info.get("file_path")
        if not remote_path:
            return None
        url = f"https://api.telegram.org/file/bot{token}/{remote_path}"
        target_dir.mkdir(parents=True, exist_ok=True)
        # use the remote filename so duplicate uploads don't collide too badly
        local = target_dir / Path(remote_path).name
        with httpx.Client(timeout=30.0) as c:
            d = c.get(url)
            d.raise_for_status()
            local.write_bytes(d.content)
        return local
    except Exception as e:  # noqa: BLE001
        logging.error("download_telegram_file failed: %s", e)
        return None


def handle_photo(api: str, token: str, msg: dict, chat_id: int,
                 authorized: bool) -> str:
    """Process an inbound photo: download -> analyze_image.py -> short reply."""
    if not authorized:
        return (
            f"unauthorized chat_id {chat_id} - photo analysis disabled. "
            f"Add your id to TPM_TELEGRAM_ALLOWED_USERS in .env."
        )
    photos = msg.get("photo") or []
    if not photos:
        return "[bridge] no photo payload"
    # photo array is sorted small -> large; pick the biggest size
    biggest = max(photos, key=lambda p: p.get("file_size", 0))
    file_id = biggest.get("file_id")
    if not file_id:
        return "[bridge] photo missing file_id"

    caption = (msg.get("caption") or "").strip()

    local = _download_telegram_file(api, token, file_id, TELEGRAM_PHOTOS_DIR)
    if local is None or not local.is_file():
        return "[bridge] photo download failed"

    script = SCRIPTS / "analyze_image.py"
    if not script.is_file():
        return f"[bridge] {script.name} missing - vision worker not available"

    args = [str(script), str(local)]
    if caption:
        args += ["--prompt", caption]
    raw = _run_py(args, CLI_TIMEOUT_S)

    # analyze_image.py prints a summary + writes JSON. Surface a compact
    # multi-line reply: top of stdout + the JSON path if we can find it.
    head = "\n".join(raw.splitlines()[:30])
    return (
        f"[vision] {local.name}"
        + (f"\ncaption: {caption}" if caption else "")
        + f"\n\n{head}"
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------
def dispatch(text: str, chat_id: int, user: dict, authorized: bool) -> str:
    """Return reply text. Built-in commands return immediately; plain text
    is forwarded to the LLM CLI only for authorized users."""
    if not text:
        return ""
    if text.startswith("/me"):
        return _cmd_me(chat_id, user)
    if text in ("/start", "/help"):
        body = HELP_TEXT
        if not authorized:
            body += (
                f"\nNOTE: chat_id {chat_id} is NOT in the allowlist; "
                f"plain-text questions are disabled. Use /me to see your id."
            )
        return body

    if not authorized:
        return (
            f"unauthorized chat_id {chat_id}. Run /me to get your id, "
            f"add it to TPM_TELEGRAM_ALLOWED_USERS in .env, restart bridge."
        )

    if text.startswith("/status"):
        return _cmd_status()
    if text.startswith("/defect"):
        return _cmd_defect(text[len("/defect"):])
    if text.startswith("/pm"):
        return _cmd_pm(text[len("/pm"):])
    if text.startswith("/calc"):
        return _cmd_calc(text[len("/calc"):])
    if text.startswith("/"):
        return f"unknown command: {text.split()[0]}. /help for list."
    return _call_cli(text)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%H:%M:%S",
    )
    _load_env(ENV_PATH)

    token = os.environ.get("TPM_TELEGRAM_BOT_TOKEN", "")
    if not token:
        print("ERROR: TPM_TELEGRAM_BOT_TOKEN missing from .env")
        return 2
    bot_user = os.environ.get("TPM_TELEGRAM_BOT_USERNAME", "<bot>")
    allowlist = _parse_allowlist(os.environ.get("TPM_TELEGRAM_ALLOWED_USERS", ""))
    api = f"https://api.telegram.org/bot{token}"

    if not allowlist:
        logging.warning(
            "TPM_TELEGRAM_ALLOWED_USERS is empty - everyone can hit /me + "
            "/help but plain text is blocked. Configure after first /me."
        )
    else:
        logging.info("allowlist active: %s", sorted(allowlist))

    # getMe sanity
    try:
        r = httpx.get(f"{api}/getMe", timeout=10.0)
        r.raise_for_status()
        me = r.json().get("result", {})
        logging.info("Connected as @%s (id=%s)", me.get("username"), me.get("id"))
    except Exception as e:  # noqa: BLE001
        logging.error("getMe failed - check token: %s", e)
        return 3

    # Register commands with Telegram for autocomplete
    _set_my_commands(api, [
        ("me",      "Show your chat_id (for allowlist setup)"),
        ("help",    "Show command list"),
        ("status",  "Ollama + bridge health"),
        ("defect",  "Mold defect lookup, e.g. /defect Flash"),
        ("pm",      "PM history, e.g. /pm M-101 status"),
        ("calc",    "Quick SymPy calc, e.g. /calc 50000/2.5e-5"),
    ])

    offset = 0
    logging.info("Polling. Talk to @%s. Ctrl+C to stop.", bot_user)
    while True:
        try:
            r = httpx.get(
                f"{api}/getUpdates",
                params={"offset": offset, "timeout": POLL_TIMEOUT_S},
                timeout=HTTP_TIMEOUT_S,
            )
            r.raise_for_status()
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message") or {}
                chat = msg.get("chat") or {}
                user = msg.get("from") or {}
                chat_id = chat.get("id")
                if not chat_id:
                    continue
                authorized = (not allowlist) or (chat_id in allowlist)
                auth_tag = "AUTH" if authorized and allowlist else ("OPEN" if authorized else "DENY")
                has_photo = bool(msg.get("photo"))
                text = (msg.get("text") or "").strip()

                if has_photo:
                    logging.info("<- %s (%s@%s): [photo]", chat_id, auth_tag,
                                 user.get("username", "?"))
                    _send_typing(api, chat_id)
                    reply = handle_photo(api, token, msg, chat_id, authorized)
                elif text:
                    logging.info("<- %s (%s@%s): %s", chat_id, auth_tag,
                                 user.get("username", "?"), text[:120])
                    _send_typing(api, chat_id)
                    reply = dispatch(text, chat_id, user, authorized)
                else:
                    continue  # ignore stickers / locations / other media for now

                _send_message(api, chat_id, reply)
                logging.info("-> %s: (%d chars)", chat_id, len(reply))
        except KeyboardInterrupt:
            logging.info("interrupted - exiting")
            return 0
        except httpx.HTTPError as e:
            logging.warning("HTTP error during getUpdates: %s; retry in 5s", e)
            time.sleep(5)
        except Exception as e:  # noqa: BLE001
            logging.error("unexpected error: %s; retry in 5s", e)
            time.sleep(5)


if __name__ == "__main__":
    sys.exit(main())
