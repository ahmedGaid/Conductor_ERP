@echo off
rem ============================================================================
rem  Conductor ERP - single-file launcher (Phase 11).
rem  Double-click this file (or run it in a terminal). It starts the WHOLE app
rem  - API + Django/DRF static + the built React UI - in ONE foreground process
rem  (waitress + WhiteNoise). No Vite dev server, no separate windows. Close it
rem  with Ctrl+C. (Background jobs via Celery are optional and NOT started here;
rem  see Docs\RUNBOOK.md if you need scheduled reports / event notifications.)
rem ============================================================================
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Virtualenv not found at %PY%
  echo         Create it first:  py -3.13 -m venv .venv ^&^& .venv\Scripts\python -m pip install -r requirements.txt
  pause
  exit /b 1
)

rem --- Run the single-process production server, but with local-safe HTTP settings ---
set "DJANGO_SETTINGS_MODULE=config.settings.prod"
set "DJANGO_SECRET_KEY=local-run-only-secret-0123456789abcdef0123456789"
set "DJANGO_DEBUG=false"
set "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1"
set "DJANGO_SSL_REDIRECT=false"
set "DJANGO_COOKIE_SECURE=false"
set "CONDUCTOR_HOST=127.0.0.1"
set "CONDUCTOR_PORT=8000"

rem --- Refuse to start if something already owns the port. Otherwise the browser would talk to a
rem     stale/other server and logins fail with "Failed to fetch". ---
netstat -ano | findstr /R /C:"127.0.0.1:%CONDUCTOR_PORT% .*LISTENING" >nul
if not errorlevel 1 (
  echo [ERROR] Port %CONDUCTOR_PORT% is already in use - another server ^(maybe an old run.cmd or a
  echo         leftover 'manage.py runserver'^) is running. Close it first, then re-run this file.
  echo         Find it:   netstat -ano ^| findstr :%CONDUCTOR_PORT%
  echo         Stop it:   taskkill /F /PID ^<the-PID-from-above^>
  pause
  exit /b 1
)

rem --- Build the React bundle once if it isn't there yet (needs Node/npm) ---
if not exist "apps\web\dist\index.html" (
  echo [setup] Building the frontend bundle ^(first run only^)...
  pushd apps\web
  call npm install || ( echo [ERROR] npm install failed ^(is Node installed?^) & popd & pause & exit /b 1 )
  call npm run build || ( echo [ERROR] frontend build failed & popd & pause & exit /b 1 )
  popd
)

rem --- Database schema + (idempotent) baseline seed so you can log in ---
echo [setup] Applying database migrations...
"%PY%" manage.py migrate --noinput || ( echo [ERROR] migrate failed ^(is PostgreSQL running?^) & pause & exit /b 1 )

if not exist "staticfiles" (
  echo [setup] Collecting Django static files...
  "%PY%" manage.py collectstatic --noinput >nul || ( echo [ERROR] collectstatic failed & pause & exit /b 1 )
)

echo [setup] Seeding baseline users + chart of accounts ^(idempotent^)...
"%PY%" manage.py seed_identity >nul
"%PY%" manage.py seed_accounting >nul

echo.
echo ============================================================
echo   Conductor ERP is starting at  http://127.0.0.1:8000
echo   Sign in:  admin / Dev12345!
echo   Press Ctrl+C in this window to stop.
echo ============================================================
echo.

rem Open the browser only AFTER the server has had a moment to bind (a detached helper waits, so the
rem first page load doesn't race the server start), then run the server in the FOREGROUND.
start "" cmd /c "timeout /t 4 /nobreak >nul & start """" http://127.0.0.1:8000/"
"%PY%" deploy\serve_waitress.py

rem If we reach here the server stopped (Ctrl+C, or it failed to start). Keep the window open so the
rem reason stays visible instead of vanishing.
echo.
echo [stopped] The Conductor server has exited. Review any message above.
pause
endlocal
