# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    BOT_LOG_FILE=/data/bot.log

WORKDIR /app

# System deps (build tools for aiohttp/yarl, SSL/ffi headers, git for VCS deps)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential \
      python3-dev \
      libffi-dev \
      libssl-dev \
      ca-certificates \
      git \
 && rm -rf /var/lib/apt/lists/*

# Poetry 2.1.4
RUN pip install --no-cache-dir "poetry==2.1.4"

# Install dependencies first for better caching
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction --no-ansi --no-root

# Copy source and install the project (provides console scripts, etc.)
COPY src ./src
RUN poetry install --no-interaction --no-ansi

# Non-root user and writable log dir
RUN addgroup --system app \
 && adduser --system --ingroup app app \
 && mkdir -p /data \
 && chown -R app:app /data /app
USER app

EXPOSE 8000

# Run with Poetry; use module entrypoint to avoid relying on a console script name
CMD ["poetry", "run", "nancy"]