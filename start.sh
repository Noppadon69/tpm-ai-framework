#!/usr/bin/env bash
# start.sh — boot TPM AI system (WSL2 / Linux / git-bash)
# ref: MASTER_PLAN_v5.md § 22.2 Phase 0 Day 3

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

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

# ---- 4. ensure Ollama is up ---------------------------------
if command -v ollama &> /dev/null; then
    if ! pgrep -f "ollama serve" > /dev/null 2>&1 \
        && ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        nohup ollama serve > "logs/ollama.out" 2>&1 &
        echo "[ok] ollama serve started"
        sleep 2
    else
        echo "[skip] ollama already serving"
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
