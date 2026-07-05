<# :
:: ==========================================================================
:: Conductor ERP - single-file silent launcher.
:: Double-click this file. It starts the Django API (8000) and the Vite
:: frontend (5173) as HIDDEN background processes - no console windows - then
:: opens the app in a dedicated browser window. Close that browser window and
:: every background process is killed automatically.
::
:: This is a batch/PowerShell polyglot: cmd runs only the lines in the leading
:: block (it relaunches PowerShell hidden, then exits); PowerShell treats that
:: same block as a comment and runs the orchestrator below.
:: ASCII-only on purpose (PS 5.1 mangles non-ASCII here).
:: ==========================================================================
@echo off
set "CONDUCTOR_ROOT=%~dp0"
start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command "$c=[IO.File]::ReadAllText('%~f0'); Invoke-Expression $c"
exit /b
: #>

# -------------------------- PowerShell orchestrator --------------------------
$ErrorActionPreference = "SilentlyContinue"
$root = ($env:CONDUCTOR_ROOT).TrimEnd('\')
Set-Location $root
$log = Join-Path $root "conductor-dev.log"
"[{0}] launch" -f (Get-Date) | Out-File -FilePath $log -Encoding ascii

function Show-Message([string]$msg) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show($msg, "Conductor ERP") | Out-Null
}

# --- 1. virtualenv must exist ---
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Show-Message "Virtualenv not found at`n$py`n`nCreate it first:`n  python -m venv .venv`n  .\.venv\Scripts\pip install -r requirements.txt"
    exit 1
}

# --- 2. Redis (best effort; the app runs without it) ---
try {
    $svc = Get-Service Redis -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne "Running") { Start-Service Redis }
} catch { }

# --- 3. migrations (keep schema current) ---
& $py manage.py migrate --noinput *>> $log

# --- 4. frontend deps (first run only) ---
$web = Join-Path $root "apps\web"
if (-not (Test-Path (Join-Path $web "node_modules"))) {
    Push-Location $web
    & npm.cmd install *>> $log
    Pop-Location
}

# --- 5. start both servers HIDDEN, keep their process handles ---
$django = Start-Process -FilePath $py -ArgumentList "manage.py","runserver","127.0.0.1:8000" `
    -WorkingDirectory $root -WindowStyle Hidden -PassThru
$vite = Start-Process -FilePath "npm.cmd" -ArgumentList "run","dev" `
    -WorkingDirectory $web -WindowStyle Hidden -PassThru

# --- 6. wait for the frontend port (Vite auto-bumps 5173 -> 5174 -> 5175) ---
# Detect a LISTENING port (interface-agnostic) - Vite binds to localhost/IPv6, so a
# 127.0.0.1 TcpClient probe would be refused even while the server is up.
function Test-PortListening([int]$p) {
    return [bool](Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue)
}
$ports = 5173,5174,5175
$url = $null
foreach ($i in 1..120) {
    foreach ($p in $ports) { if (Test-PortListening $p) { $url = "http://localhost:$p"; break } }
    if ($url) { break }
    Start-Sleep -Milliseconds 500
}
if (-not $url) { $url = "http://localhost:5173" }

# --- 7. open a DEDICATED browser window (app mode) and wait for it to close ---
$chrome = Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"
$edge   = Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"
$edge2  = Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe"
$bexe = @($chrome, $edge, $edge2) | Where-Object { Test-Path $_ } | Select-Object -First 1
$profileDir = Join-Path $env:LOCALAPPDATA "ConductorDevBrowser"

if ($bexe) {
    # A dedicated --user-data-dir forces a brand-new, isolated browser instance (it will NOT hand
    # off to an already-running Chrome/Edge). That instance stays alive until its window is closed,
    # so WaitForExit blocks for exactly the app session. The profile path has no spaces, so no quotes.
    $browser = Start-Process -FilePath $bexe -PassThru -ArgumentList @(
        "--app=$url",
        "--user-data-dir=$profileDir",
        "--new-window",
        "--no-first-run",
        "--no-default-browser-check"
    )
    if ($browser) { $browser.WaitForExit() } else { if ($vite) { $vite.WaitForExit() } }
} else {
    # No Chromium browser: open the default browser and keep servers alive until
    # the frontend process ends (no reliable "browser closed" signal without app mode).
    Start-Process $url
    if ($vite) { $vite.WaitForExit() }
}

# --- 8. browser closed -> tear down every background process ---
function Stop-Tree($proc) { if ($proc -and $proc.Id) { & taskkill /PID $proc.Id /T /F *>> $log 2>&1 } }
function Stop-Port([int]$p) {
    Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object { & taskkill /PID $_ /T /F *>> $log 2>&1 }
}
Stop-Tree $vite
Stop-Tree $django
foreach ($p in 8000,5173,5174,5175) { Stop-Port $p }
"[{0}] shut down" -f (Get-Date) | Out-File -FilePath $log -Encoding ascii -Append
