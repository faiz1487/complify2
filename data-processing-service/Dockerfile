FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY shared /app/shared
COPY data-processing-service/requirements.txt /app/data-processing-service/requirements.txt

RUN pip install --no-cache-dir -r /app/data-processing-service/requirements.txt \
    && pip install --no-cache-dir /app/shared

COPY data-processing-service /app/data-processing-service

ENV PYTHONPATH=/app:/app/data-processing-service
WORKDIR /app/data-processing-service

EXPOSE 4003

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:4003/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4003", "--workers", "1"]
