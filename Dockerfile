# Production Dockerfile for Misconception Tutor
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app:/app/src \
    PORT=8000 \
    WEB_CONCURRENCY=1 \
    GUNICORN_THREADS=8

WORKDIR /app

# curl is only needed for the container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so this layer is cached between code changes
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Copy application source and run as an unprivileged user (uid 1000 also
# matches Hugging Face Spaces). The app needs write access to its data dirs.
COPY . /app/
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/data /app/LLM/data \
    && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT}/api/health" || exit 1

# One worker + threads: the rate limiter and session memory live in process
# memory, so more than one worker would silently loosen the limits.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} --threads ${GUNICORN_THREADS} --timeout 60 --access-logfile - backend.api:app"]
