FROM python:3.11-slim

# 1. Install system dependencies (needed for building some Python deps)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       libffi-dev \
       libssl-dev \
       curl \
       build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Poetry
RUN pip install --no-cache-dir poetry

# 3. Set workdir
WORKDIR /app

# 4. Copy dependency files first (for Docker cache efficiency)
COPY pyproject.toml poetry.lock* /app/

# 5. Install project dependencies (no dev in production)
RUN poetry install --no-interaction --no-ansi --without dev

# 6. Copy project source
COPY . /app

# 7. Run Nancy bot
CMD ["poetry", "run", "nancy"]
