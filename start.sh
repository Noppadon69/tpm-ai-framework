#!/usr/bin/env bash
# start.sh — boot TPM AI system (WSL2 / Linux / git-bash)
# ref: MASTER_PLAN_v5.md § 22.2 Phase 0 Day 3

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# ---- Bug #7 fix: strip Avast-injected SSLKEYLOGFILE -----------
# Avast antivirus sets SSLKEYLOGFILE to a kernel device path
# (\\.\aswMonFltProxy\...) so it can intercept HTTPS session keys.
# This crashes uv-bundled Python's _ssl.pyd in ssl.create_default_context
# (no OPENSSL_Applink in the bundled libcrypto). Strip it here for the
# duration of this shell + all child processes.
unset SSLKEYLOGFILE

# ---- (sitecustomize.py also covers direct python invocation) ---
# Re-create venv/Lib/site-packages/sitecustomize.py if missing so the
# fix applies to `python script.py` outside this wrapper too.
SITECUSTOM=".venv/Lib/site-packages/sitecustomize.py"
if [[ -d ".venv/Lib/site-packages" && ! -f "$SITECUSTOM" ]]; then
    cat > "$SITECUSTOM" <<'EOF'
import sys
from pathlib import Path
_repo = Path(__file__).resolve().parents[3]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))
try:
    import tpm_core._envfix  # noqa: F401
except ImportError:
    import os
    os.environ.pop("SSLKEYLOGFILE", None)
EOF
    echo "[ok] regenerated $SITECUSTOM (Bug #7 fix)"
fi

echo "============================================================"
echo "TPM AI — startup ($(date -Iseconds))"
echo "============================================================"

# ---- 1. health check (FAIL → abort) -------------------------
if [[ -f scripts/health_check.py ]]; then
    if ! python scripts/health_check.py; then
        rc=$?
        if [[ $rc -ge 2 ]]; then
            echo ">>> health_check FAIL — aborting startup"
            exit 1
        fi
        echo ">>> health_check WARN — continuing with degraded state"
    fi
fi

# ---- 2. start thermal guard daemon --------------------------
if pgrep -f "thermal_guard.py$" > /dev/null 2>&1; then
    echo "[skip] thermal_guard already running"
else
    nohup python scripts/thermal_guard.py --quiet \
        > "logs/thermal_guard.out" 2>&1 &
    echo "[ok] thermal_guard started (pid=$!)"
fi

# ---- 3. start power monitor daemon --------------------------
if pgrep -f "power_monitor.py$" > /dev/null 2>&1; then
    echo "[skip] power_monitor already running"
else
    nohup python scripts/power_monitor.py --quiet \
        > "logs/power_monitor.out" 2>&1 &
    echo "[ok] power_monitor started (pid=$!)"
fi

# ---- 4. ensure Ollama is up (with VRAM-saver env vars) ------
# Flash Attention + KV cache q8_0 = ~1 GB saved on Qwen3-8B + ~30% faster prefill
# Reference: Hermes-A3B + 128K ctx trick on 12 GB cards
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0

# OLLAMA_MODELS sanity: some Ollama Windows installs put the real registry
# inside a nested `models/` subdir (registry env -> D:\X, actual content
# at D:\X\models\manifests\...). Without this, `ollama serve` boots with
# total_blobs=0 and the API returns models:[]. Auto-correct without
# touching the user registry. Idempotent.
if [[ -n "${OLLAMA_MODELS:-}" ]]; then
    om="${OLLAMA_MODELS//\\//}"
    primary="$om/manifests/registry.ollama.ai/library"
    nested="$om/models/manifests/registry.ollama.ai/library"
    if [[ ! -d "$primary" || -z "$(ls -A "$primary" 2>/dev/null)" ]] \
        && [[ -d "$nested" && -n "$(ls -A "$nested" 2>/dev/null)" ]]; then
        export OLLAMA_MODELS="$OLLAMA_MODELS/models"
        echo "[fix] OLLAMA_MODELS auto-adjusted: nested models/ subdir detected"
        echo "      now using: $OLLAMA_MODELS"
    fi
fi

if command -v ollama &> /dev/null; then
    if ! pgrep -f "ollama serve" > /dev/null 2>&1 \
        && ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        nohup ollama serve > "logs/ollama.out" 2>&1 &
        echo "[ok] ollama serve started (FLASH_ATTENTION=1 + KV_CACHE_TYPE=q8_0)"
        sleep 2
    else
        echo "[warn] ollama already running - env vars may NOT apply to existing process"
        echo "       run bash stop.sh then bash start.sh to apply VRAM optimizations"
    fi
fi

# ---- 5. start docker services (optional in Phase 0) ---------
if [[ -f services/docker-compose.yml ]] && command -v docker &> /dev/null; then
    docker compose -f services/docker-compose.yml up -d || true
    echo "[ok] docker services started (if compose file ready)"
fi

# ---- 6. preload core models (warm) --------------------------
if command -v ollama &> /dev/null; then
    for m in qwen3:8b-instruct-q4_K_M qwen3:1.7b-instruct-q4_K_M; do
        if ollama list 2>/dev/null | grep -q "${m%%:*}"; then
            echo "[ok] $m already in registry"
        else
            echo "[skip] $m not pulled — see RUNBOOK § 1"
        fi
    done
fi

# ---- 7. Chainlit UI (Phase 4 Day 1) -------------------------
if [[ -f app.py ]]; then
    if pgrep -f "chainlit run" > /dev/null 2>&1; then
        echo "[skip] chainlit already running"
    else
        if [[ -x .venv/Scripts/chainlit ]]; then
            CHAINLIT=".venv/Scripts/chainlit"
        elif [[ -x .venv/bin/chainlit ]]; then
            CHAINLIT=".venv/bin/chainlit"
        else
            CHAINLIT="chainlit"
        fi
        nohup "$CHAINLIT" run app.py --host 0.0.0.0 --port 8000 --headless \
            > "logs/chainlit.out" 2>&1 &
        echo "[ok] chainlit started (pid=$!) on http://localhost:8000"
    fi
fi

echo "============================================================"
echo "TPM AI ready."
echo "  - Web UI: http://localhost:8000"
echo "  - CLI:    .venv/Scripts/python.exe scripts/cli_demo.py"
echo "  - Logs:   tail -f logs/*.out"
echo "  - Stop:   bash stop.sh"
echo "============================================================"
