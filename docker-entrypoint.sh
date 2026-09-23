#!/bin/sh
set -eu

if [ -n "${DATABASE_URL:-}" ]; then
    uv run alembic upgrade head
fi

exec uv run python bot.py
