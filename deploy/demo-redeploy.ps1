<#
.SYNOPSIS
  Redeploy the free public sales-demo on THIS machine (see Docs/plan/demo-deploy-plan.md - PC path).

.DESCRIPTION
  Hard-resets the repo to origin/main and rebuilds/restarts the existing docker-compose.yml stack
  (web + worker + beat + db + redis, unmodified — full fidelity, no eager-mode/SQLite compromise
  needed since this is a real Docker Desktop host, not a trimmed free-tier container).
  Called on a schedule by deploy\demo-watch-and-deploy.ps1; safe to run manually any time.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

Write-Host "[demo-redeploy] fetching origin/main..."
git fetch origin main
git reset --hard origin/main

Write-Host "[demo-redeploy] rebuilding image (cached layers reused when unchanged)..."
docker compose build

Write-Host "[demo-redeploy] restarting stack..."
docker compose up -d

$rev = (git rev-parse --short HEAD)
Write-Host "[demo-redeploy] done: $rev"
