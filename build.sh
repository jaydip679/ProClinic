#!/usr/bin/env bash
# build.sh — Render build script (runs during the BUILD phase, no DB access here)
# Migrations are intentionally absent — they run in preDeployCommand in render.yaml,
# after Render guarantees the PostgreSQL instance is reachable.
set -o errexit  # Exit immediately on any error

cd backend

pip install --upgrade pip
pip install -r ../requirements.txt

# Compile + fingerprint-hash all static assets into backend/staticfiles/
# collectstatic does NOT need the database, so it is safe to run here.
python manage.py collectstatic --no-input
