<#
.SYNOPSIS
  Restore a Conductor ERP database dump (Phase 11) - for tested-restore drills or real recovery.

.DESCRIPTION
  Restores a pg_dump custom-format file (db.dump from backup.ps1) into a target database with
  pg_restore --clean --if-exists. To honour the "periodic tested restore" policy, restore into a
  SCRATCH database (e.g. erp_restore_test) and run the app/gates against it - never trust an
  unverified backup.

  Recovering the LIVE database is destructive: stop the Conductor-* services first so nothing writes
  mid-restore, then restore into the live DB. This script refuses to touch the live name unless you
  pass -Force, as a guard against accidents.

.PARAMETER DumpPath   Path to db.dump (required).
.PARAMETER DbName     Target database to restore INTO (default erp_restore_test - a safe scratch DB).
.PARAMETER DbUser     Role (default erp).
.PARAMETER DbHost     Host (default localhost).
.PARAMETER DbPort     Port (default 5432).
.PARAMETER DbPassword Role password (else PGPASSWORD env / .pgpass).
.PARAMETER PgBin      PostgreSQL bin dir (default C:\Program Files\PostgreSQL\16\bin).
.PARAMETER CreateDb   Create the target DB first if it doesn't exist.
.PARAMETER Force      Required to restore into the live "erp" database (destructive).
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$DumpPath,
  [string]$DbName = "erp_restore_test",
  [string]$DbUser = "erp",
  [string]$DbHost = "localhost",
  [int]$DbPort = 5432,
  [string]$DbPassword = "",
  [string]$PgBin = "C:\Program Files\PostgreSQL\16\bin",
  [switch]$CreateDb,
  [switch]$Force
)

$ErrorActionPreference = "Stop"
$pgRestore = Join-Path $PgBin "pg_restore.exe"
$psql      = Join-Path $PgBin "psql.exe"
if (-not (Test-Path $DumpPath)) { throw "Dump not found: $DumpPath" }
if (-not (Test-Path $pgRestore)) { throw "pg_restore not found at $pgRestore - set -PgBin." }

if ($DbName -eq "erp" -and -not $Force) {
  throw "Refusing to restore into the LIVE 'erp' database without -Force. Stop Conductor-* services, then re-run with -Force."
}

if ($DbPassword) { $env:PGPASSWORD = $DbPassword }

if ($CreateDb) {
  Write-Host "Ensuring database '$DbName' exists..."
  & $psql --host=$DbHost --port=$DbPort --username=$DbUser --dbname=postgres `
    --command="SELECT 'exists' FROM pg_database WHERE datname='$DbName';" | Out-Null
  & $psql --host=$DbHost --port=$DbPort --username=$DbUser --dbname=postgres `
    --command="CREATE DATABASE $DbName;" 2>$null | Out-Null
}

Write-Host "Restoring $DumpPath -> database '$DbName' (clean + if-exists)..."
& $pgRestore --clean --if-exists --no-owner --no-privileges `
  --host=$DbHost --port=$DbPort --username=$DbUser --dbname=$DbName $DumpPath
# pg_restore can return non-zero on benign "does not exist, skipping" notices with --clean; surface
# the code but don't treat a partial-drop notice as fatal for a fresh scratch DB.
if ($LASTEXITCODE -ne 0) {
  Write-Warning "pg_restore exited $LASTEXITCODE (often just --clean drop notices on a fresh DB). Verify the data below."
}

Write-Host "Verifying restored row counts (a few core tables)..."
& $psql --host=$DbHost --port=$DbPort --username=$DbUser --dbname=$DbName --command="
  SELECT 'accounts' AS table, count(*) FROM accounting_account
  UNION ALL SELECT 'journals', count(*) FROM accounting_journal_entry
  UNION ALL SELECT 'users', count(*) FROM identity_user;"

if ($env:PGPASSWORD) { Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue }
Write-Host "Restore into '$DbName' finished. For a TEST restore, point .env DATABASE_URL at it and run the gates."
