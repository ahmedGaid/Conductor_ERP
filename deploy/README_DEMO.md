# Conductor ERP - demo runtime (native + ngrok, no Docker)

The public demo is **native**, two processes, no Docker:

1. **App** - `deploy\serve_demo.ps1` -> Django (prod settings) + built React SPA served by
   waitress + WhiteNoise on `127.0.0.1:8000`, backed by local PostgreSQL (`erp`/`erp`).
2. **Tunnel** - `deploy\serve_tunnel.ps1` -> **ngrok** on a PERMANENT free domain:
   **https://handclasp-ceramics-directed.ngrok-free.dev** (survives restarts/reboots).

`deploy\start_all.ps1` starts both. Sign in `admin` / `Dev12345!`.

## Permanent URL
**https://handclasp-ceramics-directed.ngrok-free.dev**
- ngrok FREE tier shows a one-time "Visit Site" interstitial to each new browser visitor - they
  click through once, then see the app. (No way around it on the free plan.)

## Start / restart manually
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\AhmedGaid\ERP\deploy\serve_demo.ps1"    # app
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\AhmedGaid\ERP\deploy\serve_tunnel.ps1"   # tunnel
# or both at once:
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\AhmedGaid\ERP\deploy\start_all.ps1"
```

## Health check
```powershell
$u = "https://handclasp-ceramics-directed.ngrok-free.dev"
$h = @{ "ngrok-skip-browser-warning" = "true" }
(Invoke-WebRequest "$u/" -Headers $h -UseBasicParsing).StatusCode                       # 200
(Invoke-WebRequest "$u/assets/index-D4hxCpyG.js" -Headers $h -UseBasicParsing).StatusCode # 200 (SPA bundle)
```

## Notes / decisions (2026-07-19)
- **Native is the canonical demo** (chosen over the Docker stack). The Docker auto-deploy setup in
  `C:\AhmedGaid\ERP-demo` (scheduled tasks `ConductorDemoWatchDeploy` + `ConductorDemoNightlyReset`)
  was **DISABLED** so it can't grab :8000 and shadow this server. Re-enable with
  `Enable-ScheduledTask -TaskName <name>` (elevated) if you ever switch back to the Docker demo.
- **Never run Docker Desktop for this demo** - its container binds :8000 on IPv6 `::1`, clients
  prefer IPv6, so it shadows this native IPv4 server -> login 500 / white page. Docker auto-start
  (HKCU Run) was removed.
- `serve_demo.ps1` `ALLOWED_HOSTS` includes the ngrok host + `.trycloudflare.com` wildcard, so a
  tunnel restart doesn't break the app.
- Launcher must NOT set `$ErrorActionPreference='Stop'` (breaks the `*>>` native-stderr redirect).
- ngrok agent must be >= 3.20 (account minimum); this machine is on 3.39.9. Update: `ngrok update`.
- Logs: `%LOCALAPPDATA%\Conductor\waitress.log` and `...\tunnel.log`.

## Not yet done
- **Auto-start on logon** - blocked for the agent by a safety guard. To enable, paste this in your
  own terminal (creates a Startup entry that runs `start_all.ps1`):
  ```powershell
  $s=[Environment]::GetFolderPath('Startup')
  '@echo off'+[Environment]::NewLine+'start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\AhmedGaid\ERP\deploy\start_all.ps1"' | Set-Content "$s\ConductorDemo.cmd" -Encoding ASCII
  ```
  Until then, a reboot needs a manual `start_all.ps1`.
