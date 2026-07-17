<#
.SYNOPSIS
  Register the two Windows Scheduled Tasks the local-PC demo deploy needs (see
  Docs/plan/demo-deploy-plan.md - PC path). Re-running replaces existing tasks. Run elevated.

.DESCRIPTION
  1. "ConductorDemoWatchDeploy"  - every $WatchMinutes, checks origin/main and redeploys if it moved.
  2. "ConductorDemoNightlyReset" - daily at $ResetAt, wipes + reseeds so the demo is clean each morning.

  Both run as the CURRENT user (not SYSTEM) via S4U logon, no password stored: `docker compose`
  needs the logged-in user's Docker Desktop session, which a SYSTEM-context task (like the
  existing backup task) cannot reach. Docker Desktop must already be set to start at login.

.PARAMETER WatchMinutes  How often to poll for new commits (default 5).
.PARAMETER ResetAt       Daily nightly-reset time, HH:mm (default 03:00).
#>
[CmdletBinding()]
param(
  [int]$WatchMinutes = 5,
  [string]$ResetAt = "03:00"
)

$ErrorActionPreference = "Stop"
$RepoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$WatchPs1   = Join-Path $RepoRoot "deploy\demo-watch-and-deploy.ps1"
$ResetPs1   = Join-Path $RepoRoot "deploy\demo-nightly-reset.ps1"
$CurrentUser = "$env:USERDOMAIN\$env:USERNAME"

$principal = New-ScheduledTaskPrincipal -UserId $CurrentUser -LogonType S4U -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# --- Watch + redeploy on new commits ---
$watchAction  = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WatchPs1`""
$watchTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
  -RepetitionInterval (New-TimeSpan -Minutes $WatchMinutes) -RepetitionDuration ([TimeSpan]::MaxValue)

Register-ScheduledTask -TaskName "ConductorDemoWatchDeploy" -Action $watchAction -Trigger $watchTrigger `
  -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "Registered 'ConductorDemoWatchDeploy' (every $WatchMinutes min)."

# --- Nightly reset ---
$resetAction  = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ResetPs1`""
$resetTrigger = New-ScheduledTaskTrigger -Daily -At $ResetAt

Register-ScheduledTask -TaskName "ConductorDemoNightlyReset" -Action $resetAction -Trigger $resetTrigger `
  -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "Registered 'ConductorDemoNightlyReset' (daily at $ResetAt)."

Write-Host ""
Write-Host "Verify either one now with, e.g.:  Start-ScheduledTask -TaskName ConductorDemoWatchDeploy"
