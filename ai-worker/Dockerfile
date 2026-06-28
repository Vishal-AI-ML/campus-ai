# Campus AI - AI Worker for Hugging Face Spaces (Docker SDK)
# FastAPI service: proof scoring, AI mentor (RAG), resume/ATS, face attendance.
FROM python:3.13-slim

# uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# System libs:
#  - build-essential + cmake: compile insightface (Cython extensions)
#  - libglib2.0-0 + libgomp1: runtime libs for opencv-headless / onnxruntime
#  - curl: health checks / debugging
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        libglib2.0-0 \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces run the container as a non-root user (UID 1000). Create it and keep
# HOME writable so model downloads (InsightFace, Chroma's ONNX embedder) cache.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/app/.venv/bin:/home/user/.local/bin:$PATH \
    INSIGHTFACE_HOME=/home/user/.insightface \
    XDG_CACHE_HOME=/home/user/.cache \
    UV_CACHE_DIR=/home/user/.cache/uv \
    UV_LINK_MODE=copy

WORKDIR /home/user/app

# Install dependencies first for better layer caching (no dev, don't build project)
COPY --chown=user pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# App source (.env is excluded via .dockerignore - secrets come from HF Secrets)
COPY --chown=user . .

# Hugging Face Spaces expect the app on port 7860
EXPOSE 7860
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860}"]
