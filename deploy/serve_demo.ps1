# Conductor ERP - demo server launcher (prod waitress, native, single process).
# Serves API + built React SPA on 127.0.0.1:8000 behind a Cloudflare tunnel.
# ALLOWED_HOSTS uses a leading-dot wildcard so ANY *.trycloudflare.com hostname works,
# which means a cloudflared restart (new random hostname) does NOT break the demo.
# NOTE: do NOT set $ErrorActionPreference='Stop' here - the '*>>' redirect below merges
# waitress's native stderr, which PowerShell 5.1 would then treat as a terminating error and
# kill the server on its first startup line.
$ErrorActionPreference = "Continue"
$logDir = "$env:LOCALAPPDATA\Conductor"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

$env:DJANGO_SETTINGS_MODULE      = "config.settings.prod"
$env:DJANGO_SECRET_KEY           = "local-demo-only-secret-0123456789abcdef0123456789"
$env:DJANGO_DEBUG                = "false"
$env:DJANGO_ALLOWED_HOSTS        = "localhost,127.0.0.1,.trycloudflare.com,handclasp-ceramics-directed.ngrok-free.dev,.ngrok-free.dev"
$env:DJANGO_CSRF_TRUSTED_ORIGINS = "https://*.trycloudflare.com,https://handclasp-ceramics-directed.ngrok-free.dev,https://*.ngrok-free.dev"
$env:DJANGO_SSL_REDIRECT         = "false"   # origin is HTTP behind Cloudflare TLS; avoid redirect loop
$env:DJANGO_COOKIE_SECURE        = "false"   # refresh cookie must set over the HTTP origin
$env:DJANGO_HSTS_SECONDS         = "0"
$env:DATABASE_URL                = "postgresql://erp:erp@localhost:5432/erp"
$env:CONDUCTOR_HOST              = "127.0.0.1"
$env:CONDUCTOR_PORT              = "8000"
$env:CONDUCTOR_THREADS           = "8"

Set-Location "C:\AhmedGaid\ERP"
& "C:\AhmedGaid\ERP\.venv\Scripts\python.exe" "C:\AhmedGaid\ERP\deploy\serve_waitress.py" *>> "$logDir\waitress.log"
