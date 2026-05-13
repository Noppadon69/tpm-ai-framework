"""
telegram_bridge.py - minimal Telegram polling bridge for TPM AI.

Reads TPM_TELEGRAM_BOT_TOKEN from .env and forwards incoming messages to the
local CLI (scripts/cli_demo.py), sending the answer back as a reply.

Why exist when services/n8n/ scaffold also targets Telegram:
  n8n needs UI clicks to attach a credential to a workflow, which we can't
  automate end-to-end. This script gives you a working bot in code TODAY;
  if you outgrow it (need multi-workflow / cron / file watcher), migrate to
  n8n then. See services/n8n/README.md for the migration gate (>= 3 flows).

Run:
    /d/tpm_workspace/.venv/Scripts/python.exe scripts/telegram_bridge.py
or in background via start.bat hook.

Stop with Ctrl+C.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

# Avast / corporate proxies inject MITM certs that aren't in certifi.
# truststore.inject_into_ssl() makes Python use the Windows cert store
# which DOES have those intermediates. Safe no-op on Linux/Mac.
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:  # noqa: BLE001
    pass


REPO_ROOT = Path(__file__).resolve().parent.parent
# .venv lives in the main checkout, not in worktrees. Walk up until found.
def _find_venv_python(start: Path) -> Path:
    for parent in [start, *start.parents]:
        cand = parent / ".venv" / "Scripts" / "python.exe"
        if cand.is_file():
            return cand
    return start / ".venv" / "Scripts" / "python.exe"  # last resort
# .env: prefer main checkout (cross-worktree shared)
def _find_env(start: Path) -> Path:
    for parent in [start, *start.parents]:
        cand = parent / ".env"
        if cand.is_file():
            return cand
    return start / ".env"
ENV_PATH = _find_env(REPO_ROOT)
PY = _find_venv_python(REPO_ROOT)
# Run subprocess from the directory that owns .tpm_context (main checkout).
# When this script lives in a worktree, REPO_ROOT is the worktree but
# .tpm_context (data_classification.yaml, etc.) is at the main checkout.
MAIN_CHECKOUT = PY.parent.parent.parent  # python.exe -> Scripts -> .venv -> root
CLI = MAIN_CHECKOUT / "scripts" / "cli_demo.py"

POLL_TIMEOUT_S = 25       # long-poll seconds Telegram holds the connection
HTTP_TIMEOUT_S = 35       # > POLL_TIMEOUT_S so the long-poll doesn't time out
CLI_TIMEOUT_S = 180       # cli_demo can take 30-90s on cold LLM


def _load_env(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


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
    # Telegram caps messages at 4096 chars; chunk if longer
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


def _call_cli(prompt: str) -> str:
    if not PY.is_file():
        return f"[bridge error] venv python not found at {PY}"
    if not CLI.is_file():
        return f"[bridge error] cli_demo.py not found at {CLI}"
    try:
        proc = subprocess.run(
            [str(PY), str(CLI), prompt],
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_S,
            cwd=str(MAIN_CHECKOUT),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        out = (proc.stdout or "").strip()
        if not out:
            err = (proc.stderr or "").strip()
            return f"[cli empty stdout, rc={proc.returncode}]\n{err[-1500:]}"
        return out
    except subprocess.TimeoutExpired:
        return f"[cli timeout {CLI_TIMEOUT_S}s] try again or use shorter prompt"
    except Exception as e:  # noqa: BLE001
        return f"[bridge exception] {type(e).__name__}: {e}"


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
    api = f"https://api.telegram.org/bot{token}"

    # Identify bot + ensure token works
    try:
        r = httpx.get(f"{api}/getMe", timeout=10.0)
        r.raise_for_status()
        me = r.json().get("result", {})
        logging.info("Connected as @%s (id=%s)", me.get("username"), me.get("id"))
    except Exception as e:  # noqa: BLE001
        logging.error("getMe failed - check token: %s", e)
        return 3

    offset = 0
    logging.info("Polling for messages. Talk to @%s in Telegram. Ctrl+C to stop.", bot_user)
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
                chat_id = (msg.get("chat") or {}).get("id")
                text = (msg.get("text") or "").strip()
                if not chat_id or not text:
                    continue
                logging.info("<- %s: %s", chat_id, text[:120])

                # ack typing while CLI runs
                _send_typing(api, chat_id)

                # simple builtin commands
                if text in ("/start", "/help"):
                    _send_message(
                        api,
                        chat_id,
                        f"TPM AI bridge online (@{bot_user}).\n"
                        f"Send any engineering question, e.g.:\n"
                        f"  what is FMEA\n"
                        f"  flash defect cause\n"
                        f"  calculate clamping force for 100x200 mm at 50 MPa\n",
                    )
                    continue

                reply = _call_cli(text)
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
