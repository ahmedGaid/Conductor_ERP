# Conductor ERP demo - start BOTH the app server and the Cloudflare tunnel (hidden).
# Invoked at logon by the "ConductorDemo" scheduled task, or run manually to bring the demo up.
Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\AhmedGaid\ERP\deploy\serve_demo.ps1'
Start-Sleep -Seconds 8   # let waitress bind :8000 before the tunnel dials it
Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\AhmedGaid\ERP\deploy\serve_tunnel.ps1'
