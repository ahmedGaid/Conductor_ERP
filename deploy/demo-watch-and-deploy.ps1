<#
.SYNOPSIS
  Poll GitHub for new commits on main and redeploy the local demo when found.

.DESCRIPTION
  A home PC has no inbound path for GitHub to push a webhook/SSH deploy (no open ports — the
  whole point of fronting it with a Cloudflare Tunnel), so instead of GitHub Actions calling us,
  we call GitHub: a scheduled task runs this every few minutes, compares local HEAD to
  origin/main, and only runs demo-redeploy.ps1 when they differ. Idle ticks cost one `git fetch`.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

git fetch origin main --quiet
$local  = (git rev-parse HEAD)
$remote = (git rev-parse origin/main)

if ($local -ne $remote) {
  Write-Host "[demo-watch] origin/main moved ($local -> $remote), redeploying..."
  & (Join-Path $PSScriptRoot "demo-redeploy.ps1")
} else {
  Write-Host "[demo-watch] up to date ($local)."
}
