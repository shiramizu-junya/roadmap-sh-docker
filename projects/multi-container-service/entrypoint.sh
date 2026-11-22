#!/bin/sh
set -e
.venv/bin/python src/manage.py migrate --noinput
exec "$@"