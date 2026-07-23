<#
.SYNOPSIS
  Register the "ConductorDemoWatchdog" scheduled task: runs demo-watchdog.ps1 every
  5 minutes and at logon, so the demo self-heals from a rogue dev server, a crashed
  waitress, or a dropped ngrok tunnel without anyone noticing. Re-running replaces it.
  Does NOT require elevation (runs as the current interactive user).
#>
[CmdletBinding()]
param([int]$IntervalMinutes = 5)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$WatchdogPs1 = Join-Path $RepoRoot "deploy\demo-watchdog.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$WatchdogPs1`""

$trigger1 = New-ScheduledTaskTrigger -Once -At (Get-Date) `
  -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$trigger2 = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName "ConductorDemoWatchdog" -Action $action `
  -Trigger @($trigger1, $trigger2) -Settings $settings -Force | Out-Null

Write-Host "Registered 'ConductorDemoWatchdog' (every $IntervalMinutes min + at logon)."
