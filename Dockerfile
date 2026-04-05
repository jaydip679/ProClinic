# syntax=docker/dockerfile:1

# ── Base image ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Prevents Python from writing .pyc files and enables real-time log output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ── System dependencies ──────────────────────────────────────────────────────
# Required by WeasyPrint (Pango, Cairo, GDK-Pixbuf) and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    # WeasyPrint / PDF rendering
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libgdk-pixbuf-2.0-0 \
    libcairo2 \
    shared-mime-info \
    # Image support (Pillow)
    libjpeg62-turbo-dev \
    zlib1g-dev \
    # PostgreSQL client libs (psycopg2-binary bundles its own, but keeps things clean)
    libpq-dev \
    # Build tools (needed for cffi / argon2)
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ────────────────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ──────────────────────────────────────────────────────
# Copy requirements first to leverage Docker layer caching
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Application source ───────────────────────────────────────────────────────
COPY . /app/

# ── Port ─────────────────────────────────────────────────────────────────────
EXPOSE 8000

# ── Default command ──────────────────────────────────────────────────────────
# Change into the Django project directory before starting the server
CMD ["python", "backend/manage.py", "runserver", "0.0.0.0:8000"]
