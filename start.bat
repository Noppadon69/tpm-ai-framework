@echo off
REM start.bat - Windows native launcher for TPM AI
REM ref: MASTER_PLAN_v5.md Section 22.2

setlocal enableextensions
cd /d "%~dp0"

echo ============================================================
echo TPM AI - startup
echo ============================================================

REM ---- 1. health check ----
if exist scripts\health_check.py (
    python scripts\health_check.py
    if errorlevel 2 (
        echo [FAIL] health_check returned critical - aborting
        exit /b 1
    )
)

REM ---- 2. thermal guard daemon ----
tasklist /fi "imagename eq pythonw.exe" /v 2>nul | findstr /i "thermal_guard" >nul
if errorlevel 1 (
    start "thermal_guard" /b pythonw scripts\thermal_guard.py --quiet
    echo [ok] thermal_guard started
) else (
    echo [skip] thermal_guard already running
)

REM ---- 3. power monitor daemon ----
tasklist /fi "imagename eq pythonw.exe" /v 2>nul | findstr /i "power_monitor" >nul
if errorlevel 1 (
    start "power_monitor" /b pythonw scripts\power_monitor.py --quiet
    echo [ok] power_monitor started
) else (
    echo [skip] power_monitor already running
)

REM ---- 4. ensure Ollama is up ----
where ollama >nul 2>&1
if not errorlevel 1 (
    tasklist /fi "imagename eq ollama.exe" 2>nul | findstr /i "ollama" >nul
    if errorlevel 1 (
        start "ollama" /b ollama serve
        echo [ok] ollama serve started
        timeout /t 2 /nobreak >nul
    ) else (
        echo [skip] ollama already serving
    )
)

REM ---- 5. docker services (optional Phase 0) ----
if exist services\docker-compose.yml (
    where docker >nul 2>&1
    if not errorlevel 1 (
        docker compose -f services\docker-compose.yml up -d
    )
)

echo ============================================================
echo TPM AI ready.
echo Stop with:  stop.bat
echo ============================================================
endlocal
