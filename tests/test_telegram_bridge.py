"""
test_telegram_bridge.py - dispatch logic + helpers, no network.

Mocks _run_py/_call_cli so we exercise routing without actually invoking
the LLM or hitting Telegram. No SSL needed.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))
for _m in [k for k in list(sys.modules) if k.startswith("tpm_") or k == "telegram_bridge"]:
    del sys.modules[_m]

import telegram_bridge as tb  # noqa: E402


PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"[PASS] {name}{(' - ' + detail) if detail else ''}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}  {detail}")


# --------------------------------------------------------------------------
# Allowlist parsing
# --------------------------------------------------------------------------
def t_allowlist_parse() -> None:
    check("allowlist: empty", tb._parse_allowlist("") == set())
    check("allowlist: single", tb._parse_allowlist("123") == {123})
    check("allowlist: comma list", tb._parse_allowlist("1, 2, 3") == {1, 2, 3})
    check("allowlist: semicolon list", tb._parse_allowlist("4;5;6") == {4, 5, 6})
    check("allowlist: drops non-digits", tb._parse_allowlist("1,abc,2") == {1, 2})


# --------------------------------------------------------------------------
# Dispatch routing
# --------------------------------------------------------------------------
USER = {"username": "tester", "first_name": "T", "last_name": "Est"}


def t_me_works_when_unauthorized() -> None:
    reply = tb.dispatch("/me", chat_id=999, user=USER, authorized=False)
    check("/me: returns chat_id even unauth", "999" in reply)
    check("/me: tells user how to authorize",
          "TPM_TELEGRAM_ALLOWED_USERS" in reply)


def t_help_works_when_unauthorized() -> None:
    reply = tb.dispatch("/help", chat_id=999, user=USER, authorized=False)
    check("/help: shows commands", "/defect" in reply and "/pm" in reply)
    check("/help: warns unauthorized", "NOT in the allowlist" in reply)


def t_plain_text_blocked_when_unauthorized() -> None:
    reply = tb.dispatch("hello", chat_id=999, user=USER, authorized=False)
    check("unauth-plain: blocked", "unauthorized" in reply.lower())
    check("unauth-plain: hints /me", "/me" in reply)


def t_unknown_command_when_authorized() -> None:
    reply = tb.dispatch("/wat", chat_id=1, user=USER, authorized=True)
    check("unknown: clear error", reply.startswith("unknown command"))


def t_calc_inline_sympy() -> None:
    reply = tb.dispatch("/calc 50000/2.5e-5", chat_id=1, user=USER, authorized=True)
    check("calc: produces a number", "2.00" in reply or "2000000" in reply,
          detail=reply[:80])


def t_calc_rejects_bad_chars() -> None:
    reply = tb.dispatch("/calc __import__('os')", chat_id=1, user=USER, authorized=True)
    check("calc: rejects unsafe input", "only digits" in reply,
          detail=reply[:120])


def t_calc_usage_when_empty() -> None:
    reply = tb.dispatch("/calc", chat_id=1, user=USER, authorized=True)
    check("calc: usage when empty", "usage:" in reply)


def t_defect_usage_when_empty() -> None:
    reply = tb.dispatch("/defect", chat_id=1, user=USER, authorized=True)
    check("defect: usage when empty", "usage:" in reply)


def t_pm_usage_when_empty() -> None:
    reply = tb.dispatch("/pm", chat_id=1, user=USER, authorized=True)
    check("pm: usage when empty", "usage:" in reply)


def t_plain_text_routes_to_cli() -> None:
    with patch.object(tb, "_call_cli", return_value="cli replied OK") as mock:
        reply = tb.dispatch("what is FMEA", chat_id=1, user=USER, authorized=True)
    check("plain-auth: cli called once", mock.call_count == 1)
    check("plain-auth: prompt passed through",
          mock.call_args.args == ("what is FMEA",))
    check("plain-auth: cli result forwarded", reply == "cli replied OK")


def t_defect_calls_subprocess() -> None:
    with patch.object(tb, "_run_py", return_value="defect output") as mock:
        reply = tb.dispatch("/defect Flash", chat_id=1, user=USER, authorized=True)
    check("defect: _run_py invoked", mock.call_count == 1)
    args, _ = mock.call_args
    check("defect: arg passed", "Flash" in " ".join(args[0]))
    check("defect: reply forwarded", reply == "defect output")


def t_pm_calls_subprocess_with_default_status() -> None:
    with patch.object(tb, "_run_py", return_value="pm output") as mock:
        tb.dispatch("/pm M-101", chat_id=1, user=USER, authorized=True)
    args, _ = mock.call_args
    cmdline = " ".join(args[0])
    check("pm: mold_id passed", "M-101" in cmdline)
    check("pm: default subcommand 'status'", cmdline.endswith("status"),
          detail=cmdline)


def t_status_includes_ollama_check() -> None:
    reply = tb.dispatch("/status", chat_id=1, user=USER, authorized=True)
    check("status: mentions ollama", "ollama:" in reply.lower())
    check("status: mentions main checkout", "main checkout:" in reply.lower())


def main() -> int:
    print("=" * 60)
    print("Telegram bridge dispatch tests")
    print("=" * 60)
    t_allowlist_parse()
    t_me_works_when_unauthorized()
    t_help_works_when_unauthorized()
    t_plain_text_blocked_when_unauthorized()
    t_unknown_command_when_authorized()
    t_calc_inline_sympy()
    t_calc_rejects_bad_chars()
    t_calc_usage_when_empty()
    t_defect_usage_when_empty()
    t_pm_usage_when_empty()
    t_plain_text_routes_to_cli()
    t_defect_calls_subprocess()
    t_pm_calls_subprocess_with_default_status()
    t_status_includes_ollama_check()

    print("-" * 60)
    if FAIL == 0:
        print(f"[PASS] all tests passed  ({PASS} assertions)")
        return 0
    print(f"[FAIL] {FAIL} failed / {PASS} passed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
