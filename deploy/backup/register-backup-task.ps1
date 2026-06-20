<#
.SYNOPSIS
  Register the nightly Conductor ERP backup as a Windows Scheduled Task (Phase 11).

.DESCRIPTION
  Creates a SYSTEM scheduled task "ConductorNightlyBackup" that runs deploy\backup\backup.ps1 every
  day at -At (default 02:00). Re-running replaces the existing task. Run elevated.

  The DB password is read from PGPASSWORD / .pgpass at run time (don't bake a secret into the task);
  set a machine .pgpass for the SYSTEM account, or pass -DbPassword to embed it (less secure).

.PARAMETER At          Daily run time, HH:mm (default 02:00).
.PARAMETER OutDir      Backup root passed through to backup.ps1 (default C:\ConductorBackups).
.PARAMETER DbPassword  Optional DB password to embed in the task arguments.
.PARAMETER RetainDays  Retention passed through (default 14).
#>
[CmdletBinding()]
param(
  [string]$At = "02:00",
  [string]$OutDir = "C:\ConductorBackups",
  [string]$DbPassword = "",
  [int]$RetainDays = 14
)

$ErrorActionPreference = "Stop"
$RepoRoot   = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$BackupPs1  = Join-Path $RepoRoot "deploy\backup\backup.ps1"
$TaskName   = "ConductorNightlyBackup"

$argList = "-NoProfile -ExecutionPolicy Bypass -File `"$BackupPs1`" -OutDir `"$OutDir`" -RetainDays $RetainDays"
if ($DbPassword) { $argList += " -DbPassword `"$DbPassword`"" }

$action    = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argList
$trigger   = New-ScheduledTaskTrigger -Daily -At $At
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
  -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "Registered scheduled task '$TaskName' (daily at $At)."
Write-Host "Run it once now to verify:  Start-ScheduledTask -TaskName $TaskName"
