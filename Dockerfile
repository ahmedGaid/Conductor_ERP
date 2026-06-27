# syntax=docker/dockerfile:1
###############################################################################
# Conductor ERP — production image (hybrid: cloud VPS *or* on-premise hardware)
#
# Single-origin design: ONE Python/Waitress process serves the REST API, the
# Django/DRF admin static, AND the compiled React SPA (apps/web/dist) via
# WhiteNoise — exactly as config/settings/prod.py + config/spa.py already wire it.
# No second web server is required; front it with Nginx/IIS only for TLS.
#
# The same image runs every role (web / worker / beat); the role is chosen by the
# command in docker-compose.yml.
###############################################################################

# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — build the React SPA (Node 24) → /web/dist
# ─────────────────────────────────────────────────────────────────────────────
FROM node:24-slim AS web-builder

WORKDIR /web

# Install deps from the lockfile first (cached unless package*.json changes).
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

# Bring in the rest of the frontend and build. `npm run build` runs the i18n
# parity gate (prebuild) → tsc -b → vite build, emitting a static bundle to dist/.
COPY apps/web/ ./
RUN npm run build


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Python 3.13 runtime (API + static + SPA, served by Waitress)
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# - PYTHONUNBUFFERED: stream the JSON logs straight to stdout (12-factor).
# - prod settings by default; compose can still override per-service.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    CONDUCTOR_HOST=0.0.0.0 \
    CONDUCTOR_PORT=8000 \
    CONDUCTOR_THREADS=8

# curl is only for the container HEALTHCHECK. psycopg[binary] + argon2-cffi ship
# manylinux wheels, so no compiler/libpq-dev is needed → a lean image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install ONLY the production dependencies. requirements.txt lists the dev/test
# tools (pytest/mypy/ruff) below a "# Dev / test" marker; cut the file there so
# they never enter the image.
COPY requirements.txt ./
RUN sed '/# Dev \/ test/q' requirements.txt > requirements.prod.txt \
    && pip install -r requirements.prod.txt

# Application source (modular monolith, settings, wsgi, celery, serve script).
COPY . .

# Drop the compiled SPA in exactly where prod settings expect it:
#   WHITENOISE_ROOT = BASE_DIR/apps/web/dist  (config/settings/prod.py)
#   config/spa.py reads apps/web/dist/index.html for the "/" shell.
COPY --from=web-builder /web/dist ./apps/web/dist

# Run as a non-root user; pre-create the writable runtime dirs (collected static
# + customer document storage / scheduled-report exports).
RUN useradd --create-home --uid 10001 conductor \
    && mkdir -p /app/staticfiles /app/storage \
    && chown -R conductor:conductor /app
USER conductor

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# entrypoint runs migrate + collectstatic for the web role (RUN_MIGRATIONS=true),
# then exec's the service command. Worker/beat skip migrations.
ENTRYPOINT ["bash", "/app/deploy/docker/entrypoint.sh"]
CMD ["python", "deploy/serve_waitress.py"]
