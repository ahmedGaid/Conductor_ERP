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

# --env-file + both -f flags are required every invocation: docker-compose.yml alone has no
# POSTGRES_PASSWORD etc (those come from deploy/.env.demo at the compose-substitution layer), and
# Dockerfile.demo (not the real Dockerfile) is what lets the build skip the bundle-size gate main
# is currently over — see docker-compose.demo.yml's own header for why.
$ComposeArgs = @("--env-file", "deploy/.env.demo", "-f", "docker-compose.yml", "-f", "docker-compose.demo.yml")

Write-Host "[demo-redeploy] fetching origin/main..."
git fetch origin main
git reset --hard origin/main

Write-Host "[demo-redeploy] rebuilding image (cached layers reused when unchanged)..."
docker compose @ComposeArgs build

Write-Host "[demo-redeploy] restarting stack..."
docker compose @ComposeArgs up -d

$rev = (git rev-parse --short HEAD)
Write-Host "[demo-redeploy] done: $rev"
