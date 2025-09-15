FROM python:3.12-alpine AS builder

WORKDIR /app

# Install build deps for wheels (aiohttp/yarl/etc.)
RUN apk add --no-cache build-base libffi-dev openssl-dev

# Copy project metadata
ADD pyproject.toml poetry.lock /app/

# Install Poetry and deps into in-project venv
RUN pip install --no-cache-dir "poetry==2.1.4"
RUN poetry config virtualenvs.in-project true
RUN poetry install --no-ansi --no-interaction --only main

# Final image
FROM python:3.12-alpine
WORKDIR /app

# Runtime libs
RUN apk add --no-cache libffi openssl

# Bring venv and metadata from builder, then project sources
COPY --from=builder /app /app
ADD . /app

# Create non-root user and set permissions
RUN addgroup -g 1000 app \
 && adduser -h /app -u 1000 -G app -D app \
 && chown -R app:app /app
USER app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Run the aiohttp bot (no gunicorn; runs on port 8000)
CMD ["/app/.venv/bin/python", "-m", "nancyai.bot"]