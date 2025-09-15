FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       libffi-dev \
       libssl-dev \
       curl \
       build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry

WORKDIR /app

COPY pyproject.toml poetry.lock* /app/

# ✅ Removed "--without dev" since you don’t have a dev group
RUN poetry install --no-interaction --no-ansi

COPY . /app

CMD ["poetry", "run", "nancy"]
