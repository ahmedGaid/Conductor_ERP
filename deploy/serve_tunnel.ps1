# Conductor ERP - ngrok named tunnel (PERMANENT free domain).
# Exposes local 127.0.0.1:8000 at a STABLE https URL that survives restarts/reboots:
#   https://handclasp-ceramics-directed.ngrok-free.dev
# Authtoken is read from ngrok's config (set once via: ngrok config add-authtoken <token>).
# Note: ngrok's FREE tier shows a one-time "Visit Site" interstitial to each new browser visitor.
# Forwarding target is pinned to 127.0.0.1 (NOT bare "8000", which lets ngrok resolve "localhost"
# and sometimes pick IPv6 [::1] first) - waitress binds IPv4 only, so an IPv6 attempt gets
# "actively refused", causing intermittent failures for real visitors (same class of bug as the
# Vite proxy IPv4 pin fixed elsewhere in this repo).
$logDir = "$env:LOCALAPPDATA\Conductor"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
& "C:\Users\Rw\AppData\Local\Microsoft\WinGet\Links\ngrok.exe" http `
  --domain=handclasp-ceramics-directed.ngrok-free.dev 127.0.0.1:8000 `
  --log "$logDir\tunnel.log" --log-format logfmt
