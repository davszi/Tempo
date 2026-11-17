#!/bin/sh
# Start TEMPO on Render. With LITESTREAM_BUCKET set, restore the database from storage first,
# then run the app under Litestream so every change is copied back (deploy/README.md).
set -eu

if [ -z "${LITESTREAM_BUCKET:-}" ]; then
    echo "LITESTREAM_BUCKET is not set: the database is NOT backed up and resets on every restart." >&2
    exec gunicorn --bind "0.0.0.0:${PORT:-10000}" --workers 1 --threads 4 'backend.hosting:hosted_app()'
fi

mkdir -p "$(dirname "$TEMPO_DATABASE")"
litestream restore -config /etc/litestream.yml -if-db-not-exists -if-replica-exists "$TEMPO_DATABASE"
exec litestream replicate -config /etc/litestream.yml \
    -exec "gunicorn --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 'backend.hosting:hosted_app()'"
