FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY shared /app/shared
COPY upload-service/requirements.txt /app/upload-service/requirements.txt

RUN pip install --no-cache-dir -r /app/upload-service/requirements.txt \
    && pip install --no-cache-dir /app/shared

COPY upload-service /app/upload-service

ENV PYTHONPATH=/app:/app/upload-service
WORKDIR /app/upload-service

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4000", "--workers", "2"]
