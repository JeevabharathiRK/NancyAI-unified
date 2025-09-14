# syntax=docker/dockerfile:1

# Minimal, production-ready image for NancyAI bot
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PIP_NO_CACHE_DIR=1 \
	PIP_DISABLE_PIP_VERSION_CHECK=1 \
	# Default log path inside container (can be overridden)
	BOT_LOG_FILE=/data/bot.log

# System deps (certs) and clean up
RUN apt-get update \
	&& apt-get install -y --no-install-recommends ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install runtime dependencies directly (robust to build-backend differences)
RUN pip install --upgrade pip \
	&& pip install \
		"python-dotenv>=1.0.0" \
		"aiogram>=3.22.0" \
		"groq>=0.8.0" \
		"requests>=2.32.5,<3.0.0"

# Copy source only
COPY src ./src

# Ensure src is importable
ENV PYTHONPATH=/app/src

# Create a non-root user and writable data dir for logs
RUN addgroup --system app \
	&& adduser --system --ingroup app app \
	&& mkdir -p /data \
	&& chown -R app:app /data /app

USER app

# Nancy runs an aiohttp app on 8000
EXPOSE 8000

# Required at runtime (set via env/compose):
#   BOT_TOKEN, GROQ_API_KEY, OMDB_API_KEY, LOG_CHANNEL_ID (optional), WEBHOOK_HOST

# Run from module to avoid packaging requirements
CMD ["python", "-m", "nancyai.bot"]

