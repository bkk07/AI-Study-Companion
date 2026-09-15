FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps — kept minimal; PyMuPDF ships wheels, but gcc is needed only if building from source
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Shared upload volume mount point — must match UPLOAD_DIR=/data/uploads in backend/.env.example
RUN mkdir -p /data/uploads

EXPOSE 8000

# Default command is the API; worker overrides this in docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
