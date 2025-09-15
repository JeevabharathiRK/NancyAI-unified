FROM python:3.12-slim

# Install build deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc libffi-dev libssl-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* /app/

# Install poetry (just to export deps)
RUN pip install "poetry==2.1.4"

# Export Poetry deps → requirements.txt → pip install
RUN poetry self add poetry-plugin-export
RUN poetry export -f requirements.txt --without-hashes -o requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . /app

ENV PYTHONPATH=/app/src
# Expose bot server port
EXPOSE 8000

# Start bot
CMD ["python", "-m", "nancyai.bot"]