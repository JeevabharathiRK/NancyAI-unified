# --- Base image ---
FROM python:3.11-slim

# --- Install dependencies ---
RUN pip install --no-cache-dir poetry

# --- Set workdir ---
WORKDIR /app

# --- Copy pyproject.toml & poetry.lock first (for caching) ---
COPY pyproject.toml poetry.lock* /app/

# Install dependencies (no dev deps if production)
RUN poetry install --no-interaction --no-ansi --without dev

# --- Copy project source ---
COPY . /app

# --- Run Nancy bot ---
CMD ["poetry", "run", "nancy"]
