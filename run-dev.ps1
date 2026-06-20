# Conductor ERP - one-click DEV launcher.
# Starts the Django API (port 8000) and the Vite frontend (port 5173), each in its own window.
# Safe to run any time: it only migrates the DB and starts servers - it never deletes data.
# ASCII-only on purpose (Windows PowerShell 5.1 mangles non-ASCII in BOM-less scripts).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "==================================================="
Write-Host " Conductor ERP - starting development environment"
Write-Host "==================================================="

# --- 1. Python virtualenv ---------------------------------------------------
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Host "ERROR: virtualenv not found at $py"
    Write-Host "Create it first:  python -m venv .venv ; .\.venv\Scripts\pip install -r requirements.txt"
    Read-Host "Press Enter to exit"
    exit 1
}

# --- 2. Redis (best effort; only background jobs need it, the app runs without it) ---
try {
    $svc = Get-Service Redis -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -ne "Running") {
        Write-Host "Starting Redis service..."
        Start-Service Redis
    }
    if ($svc) { Write-Host ("Redis: " + (Get-Service Redis).Status) }
} catch {
    Write-Host "Redis not started (optional in dev) - continuing."
}

# --- 3. Keep the database schema current (prevents missing-table errors) -----
Write-Host "Applying database migrations..."
& $py manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: migrations failed. Is PostgreSQL running and .env correct?"
    Read-Host "Press Enter to exit"
    exit 1
}

# --- 4. Frontend dependencies (first run only) ------------------------------
$web = Join-Path $root "apps\web"
if (-not (Test-Path (Join-Path $web "node_modules"))) {
    Write-Host "Installing frontend dependencies (first run)..."
    Push-Location $web
    npm install
    Pop-Location
}

# --- 5. Launch backend + frontend, each in its own window -------------------
Write-Host "Launching Django API (http://127.0.0.1:8000) ..."
Start-Process -FilePath $py `
    -ArgumentList "manage.py", "runserver", "127.0.0.1:8000" `
    -WorkingDirectory $root

Write-Host "Launching Vite frontend (http://localhost:5173) ..."
Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory $web

# --- 6. Open the browser once Vite has had a moment to boot ------------------
Start-Sleep -Seconds 5
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Conductor ERP dev is running:"
Write-Host "  API       http://127.0.0.1:8000"
Write-Host "  Frontend  http://localhost:5173"
Write-Host "  Login     admin / Dev12345!"
Write-Host ""
Write-Host "Two new windows opened (API + frontend). Close them to stop the servers."
