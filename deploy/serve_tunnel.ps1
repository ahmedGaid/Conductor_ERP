# Conductor ERP - ngrok named tunnel (PERMANENT free domain).
# Exposes local 127.0.0.1:8000 at a STABLE https URL that survives restarts/reboots:
#   https://handclasp-ceramics-directed.ngrok-free.dev
# Authtoken is read from ngrok's config (set once via: ngrok config add-authtoken <token>).
# Note: ngrok's FREE tier shows a one-time "Visit Site" interstitial to each new browser visitor.
$logDir = "$env:LOCALAPPDATA\Conductor"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
& "C:\Users\Rw\AppData\Local\Microsoft\WinGet\Links\ngrok.exe" http `
  --domain=handclasp-ceramics-directed.ngrok-free.dev 8000 `
  --log "$logDir\tunnel.log" --log-format logfmt
