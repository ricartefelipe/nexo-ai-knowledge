#!/bin/sh
set -eu

alembic upgrade head
exec python -m nexo_ai
