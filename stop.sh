#!/usr/bin/env bash
# stop.sh — graceful shutdown
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "============================================================"
echo "TPM AI — shutdown ($(date -Iseconds))"
echo "============================================================"

# ---- 1. stop UI ---------------------------------------------
pkill -f "chainlit run" 2>/dev/null && echo "[ok] chainlit stopped" || echo "[skip] chainlit not running"

# ---- 2. stop daemons ----------------------------------------
for proc in thermal_guard.py power_monitor.py; do
    if pkill -f "$proc$" 2>/dev/null; then
        echo "[ok] $proc stopped"
    else
        echo "[skip] $proc not running"
    fi
done

# ---- 3. unload models ---------------------------------------
if command -v ollama &> /dev/null; then
    for m in $(ollama ps 2>/dev/null | tail -n +2 | awk '{print $1}'); do
        ollama stop "$m" 2>/dev/null && echo "[ok] unloaded $m" || true
    done
fi

# ---- 4. stop docker services --------------------------------
if [[ -f services/docker-compose.yml ]] && command -v docker &> /dev/null; then
    docker compose -f services/docker-compose.yml stop || true
fi

# ---- 5. auto-commit knowledge -------------------------------
if [[ -d .tpm_context/.git ]]; then
    git -C .tpm_context add -A
    if ! git -C .tpm_context diff --cached --quiet; then
        git -C .tpm_context commit -m "auto-commit on shutdown $(date -Iseconds)" || true
        echo "[ok] knowledge committed"
    else
        echo "[skip] no knowledge changes"
    fi
fi

echo "============================================================"
echo "TPM AI stopped cleanly."
echo "============================================================"
