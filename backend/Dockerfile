FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps — PyMuPDF ships wheels (gcc only if building from source);
# tesseract-ocr (+ English data) powers the hybrid pipeline's scanned-page branch (worker).
# redis-server + supervisor power the single-container DEMO image (api + worker + loopback redis).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    redis-server \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the local embedding model so workers never download at runtime.
# Must match LOCAL_MODEL in app/services/ai/embedding_client.py.
ENV FASTEMBED_CACHE_PATH=/app/.fastembed-cache
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

COPY . .

# Shared upload volume mount point — must match UPLOAD_DIR=/data/uploads in backend/.env.example
RUN mkdir -p /data/uploads /var/log/supervisor

# Demo single-container defaults: bundled loopback Redis.
# Any REDIS_URL / CELERY_* supplied at runtime (Railway dashboard, docker -e / --env-file,
# docker-compose environment:) takes precedence — no secrets are baked into the image.
ENV REDIS_URL=redis://127.0.0.1:6379/0 \
    CELERY_BROKER_URL=redis://127.0.0.1:6379/0 \
    CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import os, urllib.request; p = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://127.0.0.1:{p}/api/v1/health')"

# Demo entrypoint: supervisord runs bundled redis + api + worker in one container.
# (docker-compose api/worker services override this command and use the shared `redis` service instead.)
CMD ["supervisord", "-c", "/app/supervisord.conf"]
