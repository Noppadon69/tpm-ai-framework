@echo off
REM stop.bat - graceful shutdown
setlocal enableextensions
cd /d "%~dp0"

echo ============================================================
echo TPM AI - shutdown
echo ============================================================

REM ---- 1. stop chainlit (Phase 4+) ----
taskkill /f /im chainlit.exe 2>nul && echo [ok] chainlit stopped || echo [skip] chainlit not running

REM ---- 2. stop daemons (best-effort: kill pythonw with thermal/power) ----
for /f "tokens=2" %%p in ('tasklist /fi "imagename eq pythonw.exe" /v 2^>nul ^| findstr /i "thermal_guard"') do (
    taskkill /f /pid %%p 2>nul
)
for /f "tokens=2" %%p in ('tasklist /fi "imagename eq pythonw.exe" /v 2^>nul ^| findstr /i "power_monitor"') do (
    taskkill /f /pid %%p 2>nul
)
echo [ok] daemons signaled

REM ---- 3. docker services ----
if exist services\docker-compose.yml (
    where docker >nul 2>&1
    if not errorlevel 1 docker compose -f services\docker-compose.yml stop
)

REM ---- 4. auto-commit knowledge ----
if exist .tpm_context\.git (
    git -C .tpm_context add -A
    git -C .tpm_context commit -m "auto-commit on shutdown" 2>nul && echo [ok] knowledge committed || echo [skip] no changes
)

echo ============================================================
echo TPM AI stopped.
echo ============================================================
endlocal
