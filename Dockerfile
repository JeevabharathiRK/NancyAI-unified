# syntax=docker/dockerfile:1

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

# Poetry 2.1.4 as requested
RUN pip install --no-cache-dir "poetry==2.1.4"

# Install dependency groups (runtime only) without installing the project yet
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-interaction --no-ansi --only main --no-root

# Copy source and install the project (to provide the "nancy" console script)
COPY src ./src
RUN poetry install --no-interaction --no-ansi --only main

# Non-root user and writable log dir
RUN addgroup --system app \
 && adduser --system --ingroup app app \
 && mkdir -p /data \
 && chown -R app:app /data /app
USER app

EXPOSE 8000

# Run via Poetry
CMD ["poetry", "run", "python", "-m", "nancyai.bot"]

