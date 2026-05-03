# Cron / Scheduler Setup

> Schedules for automated tasks. Manual runs always work; this is just for convenience.

---

## 1. Night Cycle — every weekday 23:00 (or anytime overnight)

Runs `scripts/night_cycle.py` to replay daytime sessions, audit prompt budgets,
and write tomorrow's morning brief.

### Linux / WSL2 (cron)

```bash
crontab -e
```

```cron
# Night cycle - weekdays at 23:00 local time
0 23 * * 1-5  cd /path/to/tpm_workspace && .venv/bin/python scripts/night_cycle.py --quiet >> logs/night_cycle.log 2>&1
```

### Windows (Task Scheduler)

```
Task name:   TPM AI Night Cycle
Trigger:     Daily, Weekdays only, 23:00
Action:      D:\tpm_workspace\.venv\Scripts\python.exe
Arguments:   scripts\night_cycle.py --quiet
Start in:    D:\tpm_workspace
Conditions:  Only when computer is on AC power (battery-aware - see § 3.3)
             Wake the computer to run this task: NO (don't drain battery)
```

PowerShell one-liner to register:
```powershell
$action = New-ScheduledTaskAction `
    -Execute "D:\tpm_workspace\.venv\Scripts\python.exe" `
    -Argument "scripts\night_cycle.py --quiet" `
    -WorkingDirectory "D:\tpm_workspace"

$trigger = New-ScheduledTaskTrigger -Daily -DaysInterval 1 -At "23:00"

$settings = New-ScheduledTaskSettingsSet `
    -DisallowStartIfOnBatteries `
    -StopIfGoingOnBatteries `
    -StartWhenAvailable

Register-ScheduledTask -TaskName "TPM AI Night Cycle" `
    -Action $action -Trigger $trigger -Settings $settings -Force
```

---

## 2. Weekly Progress Slides — every Friday 17:00

Runs `scripts/weekly_progress.py` to generate `.pptx` for review.

### Linux / WSL2 (cron)

```cron
# Weekly progress - Fridays at 17:00 local time
0 17 * * 5  cd /path/to/tpm_workspace && .venv/bin/python scripts/weekly_progress.py --quiet >> logs/weekly_progress.log 2>&1
```

### Windows (Task Scheduler)

```
Task name:   TPM AI Weekly Progress
Trigger:     Weekly, Friday 17:00
Action:      D:\tpm_workspace\.venv\Scripts\python.exe
Arguments:   scripts\weekly_progress.py --quiet
Start in:    D:\tpm_workspace
```

PowerShell:
```powershell
$action = New-ScheduledTaskAction `
    -Execute "D:\tpm_workspace\.venv\Scripts\python.exe" `
    -Argument "scripts\weekly_progress.py --quiet" `
    -WorkingDirectory "D:\tpm_workspace"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Friday -At "17:00"

Register-ScheduledTask -TaskName "TPM AI Weekly Progress" `
    -Action $action -Trigger $trigger -Force
```

---

## 3. Auto-commit / GitHub backup — every 4h + push 23:00

(Phase 1+ — when scripts/github_backup.py exists)

```cron
# Local commit every 4h
0 */4 * * *  cd /path/to/tpm_workspace && .venv/bin/python scripts/github_backup.py --no-push

# Daily push at 23:30 (after night cycle)
30 23 * * *  cd /path/to/tpm_workspace && .venv/bin/python scripts/github_backup.py --push

# Weekly snapshot tag
0 2 * * 0    cd /path/to/tpm_workspace && .venv/bin/python scripts/github_backup.py --snapshot-tag
```

---

## 4. Manual runs (anytime)

```powershell
# Night cycle (any date, any model)
.venv\Scripts\python.exe scripts\night_cycle.py
.venv\Scripts\python.exe scripts\night_cycle.py --date 2026-05-03
.venv\Scripts\python.exe scripts\night_cycle.py --heavy --max-replays 5

# Weekly progress (any window)
.venv\Scripts\python.exe scripts\weekly_progress.py
.venv\Scripts\python.exe scripts\weekly_progress.py --end 2026-05-09 --json
.venv\Scripts\python.exe scripts\weekly_progress.py --days 14
```

---

## Verification

After registering tasks, verify they ran:

```powershell
# Windows - last run results
Get-ScheduledTask -TaskName "TPM AI*" | Get-ScheduledTaskInfo

# Logs
Get-Content logs\night_cycle.log -Tail 30
Get-Content logs\weekly_progress.log -Tail 30
```

```bash
# Linux/WSL
grep CRON /var/log/syslog | tail -20
tail -30 logs/night_cycle.log
```

---

## Removal

```powershell
Unregister-ScheduledTask -TaskName "TPM AI Night Cycle" -Confirm:$false
Unregister-ScheduledTask -TaskName "TPM AI Weekly Progress" -Confirm:$false
```

```bash
# Linux/WSL: edit and delete the lines
crontab -e
```
