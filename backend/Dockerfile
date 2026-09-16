FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps — PyMuPDF ships wheels (gcc only if building from source);
# tesseract-ocr (+ English data) powers the hybrid pipeline's scanned-page branch (worker).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the local embedding model so workers never download at runtime.
# Must match LOCAL_MODEL in app/services/ai/embedding_client.py.
ENV FASTEMBED_CACHE_PATH=/app/.fastembed-cache
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

COPY . .

# Shared upload volume mount point — must match UPLOAD_DIR=/data/uploads in backend/.env.example
RUN mkdir -p /data/uploads

EXPOSE 8000

# Default command is the API; worker overrides this in docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
