#!/bin/sh
set -eu

if [ -z "${ALLOWED_HOSTS:-}" ] && [ -n "${RENDER_EXTERNAL_HOSTNAME:-}" ]; then
    export ALLOWED_HOSTS="$RENDER_EXTERNAL_HOSTNAME"
fi

python manage.py check --deploy --fail-level WARNING
python manage.py migrate --check --noinput
python manage.py collectstatic --noinput --verbosity 0
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-10000}" --workers 1 --threads 4
