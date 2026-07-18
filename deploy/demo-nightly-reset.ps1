<#
.SYNOPSIS
  Nightly demo reset for the local-PC deploy (see Docs/plan/demo-deploy-plan.md - PC path).

.DESCRIPTION
  Wipes the demo db/storage/redis volumes and reseeds from scratch, so the public sales demo
  always starts the day clean regardless of what a prospect (or you, live) did to it the day
  before. Windows/PowerShell twin of deploy\demo-nightly-reset.sh (that one is for the shelved
  VM/Linux path). DESTRUCTIVE BY DESIGN — never point this at a real customer install.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

# Same flags as demo-redeploy.ps1 — required every invocation (secrets + demo Dockerfile live
# outside docker-compose.yml). See that script / docker-compose.demo.yml for why.
$ComposeArgs = @("--env-file", "deploy/.env.demo", "-f", "docker-compose.yml", "-f", "docker-compose.demo.yml")

Write-Host "[demo-reset] tearing down stack + volumes..."
docker compose @ComposeArgs down -v

Write-Host "[demo-reset] starting fresh stack..."
docker compose @ComposeArgs up -d

Write-Host "[demo-reset] waiting for 'web' to report healthy..."
$healthy = $false
for ($i = 0; $i -lt 30; $i++) {
  try {
    docker compose @ComposeArgs exec -T web curl -fsS http://localhost:8000/health | Out-Null
    $healthy = $true
    break
  } catch {
    Start-Sleep -Seconds 5
  }
}
if (-not $healthy) { Write-Warning "[demo-reset] 'web' never reported healthy after 150s — seeding anyway." }

Write-Host "[demo-reset] seeding demo data..."
docker compose @ComposeArgs exec -T web python manage.py seed_identity
docker compose @ComposeArgs exec -T web python manage.py seed_accounting
docker compose @ComposeArgs exec -T web python scripts/seed_demo.py

Write-Host "[demo-reset] done."
