# ==============================================================================
# Interview Practice Coach - Backend Production Dockerfile
# Multi-stage / lightweight Python 3.11 container with faster-whisper support
# ==============================================================================

FROM python:3.11-slim AS runtime

# Set security and Python runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    WHISPER_MODEL_SIZE=tiny \
    WHISPER_DEVICE=cpu \
    WHISPER_COMPUTE_TYPE=int8 \
    HF_HOME=/app/models_cache \
    PRACTICE_COACH_DB_PATH=/app/data/practice_coach.db

WORKDIR /app

# Install runtime system packages:
# - ffmpeg: required for audio format transcoding in faster-whisper / PyAV
# - curl: required for Docker container health check probing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-privileged user and writable persistent directories
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /app/models_cache && \
    chown -R appuser:appuser /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/

# Switch to non-privileged user
USER appuser

EXPOSE 8000

# Container healthcheck testing /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# Production startup command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
