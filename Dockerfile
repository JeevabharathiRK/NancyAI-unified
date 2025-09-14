# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    BOT_LOG_FILE=/data/bot.log

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Poetry
RUN pip install --upgrade pip && pip install "poetry==2.1.4"

# Copy project metadata first for better layer caching
COPY pyproject.toml poetry.lock* ./
# Install only main/runtime deps; don’t install project package as editable
RUN poetry install --only main --no-interaction --no-ansi

# Copy source
COPY src ./src
ENV PYTHONPATH=/app/src

# Create non-root user and writable log dir
RUN addgroup --system app \
 && adduser --system --ingroup app app \
 && mkdir -p /data \
 && chown -R app:app /data /app
USER app

EXPOSE 8000

# If you have a console_script named "nancy", switch CMD to ["poetry", "run", "nancy"]
CMD ["poetry", "run", "nancy"]