<#
.SYNOPSIS
  Nightly Conductor ERP backup: PostgreSQL dump + document storage, with retention (Phase 11).

.DESCRIPTION
  Implements the DECISIONS backup policy ("automated nightly backups with periodic tested
  restores"). Produces, per run, into -OutDir\<yyyy-MM-dd_HHmmss>\:
    db.dump         - pg_dump custom format (compressed, restorable with pg_restore)
    storage.zip     - the document/report storage tree (if -StorageRoot exists)
    MANIFEST.txt    - what was captured, sizes, the exact restore command
  Then deletes run folders older than -RetainDays.

  Register it to run nightly with deploy\backup\register-backup-task.ps1. Verify restores
  PERIODICALLY with deploy\backup\restore.ps1 against a scratch database - an untested backup is
  not a backup.

.PARAMETER OutDir        Backup root (default C:\ConductorBackups).
.PARAMETER DbName        Database (default erp).
.PARAMETER DbUser        Role (default erp).
.PARAMETER DbHost        Host (default localhost).
.PARAMETER DbPort        Port (default 5432).
.PARAMETER DbPassword    Role password. If omitted, uses the PGPASSWORD env var or a .pgpass entry.
.PARAMETER StorageRoot   Document storage to archive (default C:\ConductorData\storage).
.PARAMETER PgBin         PostgreSQL bin dir (default C:\Program Files\PostgreSQL\16\bin).
.PARAMETER RetainDays    Keep this many days of runs (default 14).
#>
[CmdletBinding()]
param(
  [string]$OutDir = "C:\ConductorBackups",
  [string]$DbName = "erp",
  [string]$DbUser = "erp",
  [string]$DbHost = "localhost",
  [int]$DbPort = 5432,
  [string]$DbPassword = "",
  [string]$StorageRoot = "C:\ConductorData\storage",
  [string]$PgBin = "C:\Program Files\PostgreSQL\16\bin",
  [int]$RetainDays = 14
)

$ErrorActionPreference = "Stop"
$pgDump = Join-Path $PgBin "pg_dump.exe"
if (-not (Test-Path $pgDump)) { throw "pg_dump not found at $pgDump - set -PgBin." }

$stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$runDir = Join-Path $OutDir $stamp
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

if ($DbPassword) { $env:PGPASSWORD = $DbPassword }

# 1. Database: custom-format dump (the canonical, restorable artifact).
$dumpPath = Join-Path $runDir "db.dump"
Write-Host "Dumping database '$DbName' -> $dumpPath"
& $pgDump --format=custom --no-owner --no-privileges `
  --host=$DbHost --port=$DbPort --username=$DbUser --dbname=$DbName --file=$dumpPath
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed with exit code $LASTEXITCODE" }

# 2. Document storage (best-effort; an install with no uploads yet simply skips it).
$storageNote = "skipped (not present)"
if (Test-Path $StorageRoot) {
  $zipPath = Join-Path $runDir "storage.zip"
  Write-Host "Archiving storage '$StorageRoot' -> $zipPath"
  Compress-Archive -Path (Join-Path $StorageRoot "*") -DestinationPath $zipPath -Force
  $storageNote = "storage.zip ($([math]::Round((Get-Item $zipPath).Length/1MB,2)) MB)"
}

# 3. Manifest with the exact restore command (so a future operator needs no notes).
$dbMb = [math]::Round((Get-Item $dumpPath).Length / 1MB, 2)
@"
Conductor ERP backup
Taken:    $stamp
Database: $DbName @ ${DbHost}:$DbPort  (db.dump, $dbMb MB, pg_dump custom format)
Storage:  $storageNote

Restore (into a scratch DB to TEST, or the live DB to RECOVER):
  deploy\backup\restore.ps1 -DumpPath "$dumpPath" -DbName <target-db>
"@ | Set-Content -Path (Join-Path $runDir "MANIFEST.txt") -Encoding utf8

# 4. Retention: drop runs older than RetainDays.
$cutoff = (Get-Date).AddDays(-$RetainDays)
Get-ChildItem -Path $OutDir -Directory |
  Where-Object { $_.LastWriteTime -lt $cutoff } |
  ForEach-Object { Write-Host "Pruning old backup $($_.Name)"; Remove-Item $_.FullName -Recurse -Force }

if ($env:PGPASSWORD) { Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue }
Write-Host "Backup complete: $runDir"
