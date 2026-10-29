# Production Dockerfile for Misconception Tutor
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . /app/

# Environment variables
ENV PYTHONPATH=/app \
    BACKEND_HOST=0.0.0.0 \
    BACKEND_PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# Start server
CMD ["python", "-m", "backend.api"]
