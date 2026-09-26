#!/bin/sh
# A throwaway backend for the end-to-end tests: its own database and uploads under backend/.e2e/, the
# demo data, on port 8001, so a run never touches the dev database.
set -e
cd "$(dirname "$0")/../../backend"
PYTHON="${PYTHON:-../.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON=python
export DJANGO_DEBUG=1 DJANGO_SQLITE_PATH=.e2e/db.sqlite3 DJANGO_MEDIA_ROOT=.e2e/media
export DJANGO_CORS_ALLOWED_ORIGINS=http://127.0.0.1:5174
rm -rf .e2e && mkdir -p .e2e
"$PYTHON" manage.py migrate -v0
"$PYTHON" manage.py seed_demo >/dev/null
exec "$PYTHON" manage.py runserver 127.0.0.1:8001 --noreload
