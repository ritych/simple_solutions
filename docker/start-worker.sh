#!/bin/sh
set -eu

# Migrations are applied by the API container before it becomes healthy.
python -m app.collect_once || echo "Initial collection failed, the schedule will retry" >&2
exec python -m celery -A app.worker:celery_app worker --beat --loglevel=INFO --pool=solo
