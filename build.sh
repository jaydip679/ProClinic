#!/usr/bin/env bash
# build.sh — Render build script (runs during every deploy, before the service starts)
set -o errexit  # Exit immediately on any error

cd backend

pip install --upgrade pip
pip install -r ../requirements.txt

# Compile + fingerprint-hash all static assets into backend/staticfiles/
python manage.py collectstatic --no-input

# Apply any pending database migrations
python manage.py migrate
