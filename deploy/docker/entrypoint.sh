#!/usr/bin/env bash
# Conductor ERP — container entrypoint.
#
# One image serves every role (web / worker / beat). Only the web role owns the
# schema + collected static, so DB migrations and collectstatic are gated behind
# RUN_MIGRATIONS=true (set on the `web` service only) to avoid three containers
# racing to migrate on boot.
set -euo pipefail

if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
  echo "[entrypoint] applying database migrations…"
  python manage.py migrate --noinput

  echo "[entrypoint] collecting Django/DRF static (admin)…"
  # The React bundle is served straight from apps/web/dist via WHITENOISE_ROOT;
  # collectstatic only gathers Django's own admin/DRF assets into STATIC_ROOT.
  python manage.py collectstatic --noinput
fi

exec "$@"
