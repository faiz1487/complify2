FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY shared /app/shared
COPY retrieval-service/requirements.txt /app/retrieval-service/requirements.txt

RUN pip install --no-cache-dir -r /app/retrieval-service/requirements.txt \
    && pip install --no-cache-dir /app/shared

COPY retrieval-service /app/retrieval-service

ENV PYTHONPATH=/app:/app/retrieval-service
WORKDIR /app/retrieval-service

EXPOSE 4002

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4002/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4002", "--workers", "2"]
