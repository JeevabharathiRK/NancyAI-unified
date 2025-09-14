# syntax=docker/dockerfile:1

# Minimal, production-ready image for NancyAI bot
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    BOT_LOG_FILE=/data/bot.log

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry==1.8.3"

# Install deps first for better caching
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction --no-ansi --only main

# Copy source
COPY src ./src
ENV PYTHONPATH=/app/src

# Non-root user and writable log dir
RUN addgroup --system app \
 && adduser --system --ingroup app app \
 && mkdir -p /data \
 && chown -R app:app /data /app
USER app

EXPOSE 8000

# Run via Poetry as requested
CMD ["poetry", "run", "python", "-m", "nancyai.bot"]

