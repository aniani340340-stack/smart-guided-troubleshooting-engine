# Multi-stage lightweight Dockerfile for Samsung Smart Guided Troubleshooting Engine
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install system curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and data
COPY . /app/theme02_troubleshooting_engine

# Set python path to find theme02_troubleshooting_engine package
ENV PYTHONPATH=/app

# Pre-warm the cache and verify index integrity
RUN python /app/theme02_troubleshooting_engine/prewarm_cache.py

# Expose microservice port
EXPOSE 8000

# Docker healthcheck querying /health endpoint
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI service
CMD ["uvicorn", "theme02_troubleshooting_engine.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
