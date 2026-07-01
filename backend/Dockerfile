# Campus AI backend - FastAPI (uv, Python 3.13)
FROM python:3.13-slim

# uv (fast Python package manager) from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# curl kept for container health checks / debugging
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first for better layer caching (no project, no dev deps)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy the application source and finish the install
COPY . .
RUN uv sync --frozen --no-dev

# Security hardening: run as a non-root user (own /app so uv can read the venv)
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# PaaS hosts (Koyeb/Render) inject $PORT; default to 8000 locally
ENV PORT=8000
EXPOSE 8000

# Bind to the platform-provided port
CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
