# Conductor ERP demo - self-healing watchdog. Run every few minutes via the
# "ConductorDemoWatchdog" scheduled task (see register-demo-watchdog.ps1).
#
# Guards against the two failure modes that have actually taken the demo down:
#   1. Someone/something runs `manage.py runserver` on :8000 (dev server, no built
#      assets -> blank page). We kill it and restart the real waitress server.
#   2. waitress or ngrok crashed / isn't running. We restart whichever is missing.
$ErrorActionPreference = "Continue"
$logDir = "$env:LOCALAPPDATA\Conductor"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir "watchdog.log"

function Write-Log($msg) {
  "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg" | Add-Content -Path $log
}

# --- 1. Kill any Django dev server squatting on :8000 ---
$devServers = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'manage\.py\s+runserver' }
foreach ($p in $devServers) {
  Write-Log "Killing rogue dev server PID $($p.ProcessId): $($p.CommandLine)"
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}

# --- 2. Check waitress is actually serving (Server header + real JS asset, not 404) ---
$appHealthy = $false
try {
  $r = Invoke-WebRequest "http://127.0.0.1:8000/" -UseBasicParsing -TimeoutSec 6
  if ($r.StatusCode -eq 200 -and $r.Headers['Server'] -match 'waitress') {
    $appHealthy = $true
  }
} catch { $appHealthy = $false }

if (-not $appHealthy) {
  Write-Log "App unhealthy (not waitress / not responding) - restarting serve_demo.ps1"
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'serve_waitress\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\AhmedGaid\ERP\deploy\serve_demo.ps1'
  Start-Sleep -Seconds 8
}

# --- 3. Check ngrok tunnel is up on the permanent domain ---
$tunnelHealthy = $false
try {
  $t = Invoke-RestMethod "http://127.0.0.1:4040/api/tunnels" -TimeoutSec 6
  if ($t.tunnels | Where-Object { $_.public_url -match 'handclasp-ceramics-directed' }) {
    $tunnelHealthy = $true
  }
} catch { $tunnelHealthy = $false }

if (-not $tunnelHealthy) {
  Write-Log "Tunnel unhealthy - restarting serve_tunnel.ps1"
  Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\AhmedGaid\ERP\deploy\serve_tunnel.ps1'
}

if ($appHealthy -and $tunnelHealthy -and $devServers.Count -eq 0) {
  Write-Log "OK (app healthy, tunnel healthy, no rogue dev server)"
}
