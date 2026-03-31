#!/bin/sh
set -e

if [ "${SKIP_DB_WAIT:-0}" != "1" ]; then
  python docker/wait_for_db.py
fi

if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
  alembic upgrade head
fi

exec "$@"
