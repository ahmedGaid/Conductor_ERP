<#
.SYNOPSIS
  Stop and remove the three Conductor ERP Windows services (Phase 11).
.DESCRIPTION
  Reverses install-services.ps1. Safe to run if some services are already gone. Run elevated.
.PARAMETER Nssm
  Path to nssm.exe (default: "nssm" on PATH).
#>
[CmdletBinding()]
param([string]$Nssm = "nssm")

$ErrorActionPreference = "Continue"

foreach ($name in @("Conductor-Web", "Conductor-Worker", "Conductor-Beat")) {
  & $Nssm status $name *> $null
  if ($LASTEXITCODE -eq 0) {
    & $Nssm stop $name *> $null
    & $Nssm remove $name confirm | Out-Null
    Write-Host "removed $name"
  } else {
    Write-Host "skip $name (not installed)"
  }
}
