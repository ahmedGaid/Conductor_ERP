<#
.SYNOPSIS
  Register Conductor ERP as three Windows services using NSSM (Phase 11).

.DESCRIPTION
  Creates and starts:
    Conductor-Web     - waitress serving config.wsgi (API + Django static + the built React SPA)
    Conductor-Worker  - Celery worker (background jobs: reports, notifications, workflow)
    Conductor-Beat    - Celery beat (periodic schedule, e.g. hourly scheduled-report sweep)

  All three run under the project venv with DJANGO_SETTINGS_MODULE=config.settings.prod, auto-start
  on boot, and write rotating stdout/stderr logs under deploy\logs. Re-running is safe: each service
  is removed first, then recreated (idempotent).

  Prerequisites:
    - NSSM on PATH (https://nssm.cc) or pass -Nssm <path-to-nssm.exe>.
    - .venv created and `pip install -r requirements.txt` already run.
    - .env present at the repo root (copied from deploy\.env.prod.example and filled in).
    - PostgreSQL + Redis services installed and running.
  Run this from an elevated (Administrator) PowerShell.

.PARAMETER Nssm
  Path to nssm.exe (default: "nssm", i.e. found on PATH).

.PARAMETER Host
  Interface waitress binds to (default 127.0.0.1 - put IIS/Nginx in front for TLS).

.PARAMETER Port
  Port waitress binds to (default 8000).
#>
[CmdletBinding()]
param(
  [string]$Nssm = "nssm",
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

# Repo root is two levels up from deploy\windows\.
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python   = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$LogDir   = Join-Path $RepoRoot "deploy\logs"

if (-not (Test-Path $Python)) { throw "venv python not found at $Python - create the venv first." }
if (-not (Test-Path (Join-Path $RepoRoot ".env"))) {
  throw "No .env at $RepoRoot - copy deploy\.env.prod.example to .env and fill it in first."
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

# Shared environment for every service (NSSM AppEnvironmentExtra wants NUL-free 'KEY=VAL' lines).
$EnvLines = "DJANGO_SETTINGS_MODULE=config.settings.prod`nCONDUCTOR_HOST=$BindHost`nCONDUCTOR_PORT=$Port"

function Install-Service {
  param([string]$Name, [string]$AppArgs, [string]$DependsOn = "")

  # Idempotent: remove an existing definition before recreating.
  & $Nssm status $Name *> $null
  if ($LASTEXITCODE -eq 0) {
    & $Nssm stop $Name *> $null
    & $Nssm remove $Name confirm | Out-Null
  }

  & $Nssm install $Name $Python $AppArgs
  & $Nssm set $Name AppDirectory $RepoRoot
  & $Nssm set $Name AppEnvironmentExtra $EnvLines
  & $Nssm set $Name Start SERVICE_AUTO_START
  & $Nssm set $Name AppStdout (Join-Path $LogDir "$Name.out.log")
  & $Nssm set $Name AppStderr (Join-Path $LogDir "$Name.err.log")
  # Rotate logs at ~10 MB so they never fill the disk.
  & $Nssm set $Name AppRotateFiles 1
  & $Nssm set $Name AppRotateOnline 1
  & $Nssm set $Name AppRotateBytes 10485760
  if ($DependsOn) { & $Nssm set $Name DependOnService $DependsOn }
  Write-Host "  registered $Name"
}

Write-Host "Installing Conductor services (repo: $RepoRoot)..."

# Web: waitress (depends on Postgres being up).
Install-Service -Name "Conductor-Web" `
  -AppArgs "deploy\serve_waitress.py" -DependsOn "postgresql-x64-16"

# Celery worker: solo pool is required on Windows (prefork is POSIX-only). Depends on Redis.
Install-Service -Name "Conductor-Worker" `
  -AppArgs "-m celery -A config worker --loglevel=info --pool=solo" -DependsOn "Redis"

# Celery beat: the periodic scheduler. Depends on Redis.
Install-Service -Name "Conductor-Beat" `
  -AppArgs "-m celery -A config beat --loglevel=info" -DependsOn "Redis"

Write-Host "Starting services..."
& $Nssm start Conductor-Web
& $Nssm start Conductor-Worker
& $Nssm start Conductor-Beat

Write-Host "Done. Check status with: Get-Service Conductor-*"
