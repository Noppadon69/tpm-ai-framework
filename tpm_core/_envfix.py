"""
tpm_core._envfix - environment scrubbing run before any SSL imports.

Bug #7 PERMANENT FIX (root cause confirmed 2026-05-12):

Avast antivirus injects ``SSLKEYLOGFILE`` into the process environment
to intercept HTTPS session keys. The injected value is a kernel device
path (e.g. ``\\\\.\\aswMonFltProxy\\<addr>``), NOT a regular file.

uv-bundled python-build-standalone Python 3.12 has an ``_ssl.pyd`` whose
libcrypto was compiled WITHOUT an ``OPENSSL_Applink`` table. When
:func:`ssl.create_default_context` is called and ``SSLKEYLOGFILE`` is
set, OpenSSL tries to ``fopen()`` that path; the FILE* needs to flow back
through the host application's CRT via Applink, but the table is missing
and OpenSSL crashes with::

    OPENSSL_Uplink(<addr>,08): no OPENSSL_Applink

The crash is deterministic for ANY ``SSLKEYLOGFILE`` value on this Python
build (even legitimate file paths trigger the same fwrite -> applink
flow). So we simply strip the variable before any SSL code runs.

Diagnostic one-liner that should print "SSL OK"::

    python -c "import ssl; ssl.create_default_context(); print('SSL OK')"

Usage:
    Anywhere we boot a Python entry point (CLI, Chainlit, tests),
    ``import tpm_core._envfix`` as the FIRST import (before
    anything that might pull in ssl / urllib / httpx).

For belt-and-suspenders the venv's ``sitecustomize.py`` also calls
this module on every Python invocation.
"""
import os

_REMOVED = os.environ.pop("SSLKEYLOGFILE", None)


def was_scrubbed() -> str | None:
    """Return the SSLKEYLOGFILE value we stripped (None if env was clean)."""
    return _REMOVED
