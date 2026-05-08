FROM python:3.11-slim

LABEL org.opencontainers.image.title="vila-politica-2026"
LABEL org.opencontainers.image.description="Vila Politica 2026 - reproducible election forecasting"
LABEL org.opencontainers.image.source="https://github.com/PAMF2/vila-politica-2026"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# System deps for weasyprint, pdftotext, lxml, scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libcairo2 \
    libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    poppler-utils make build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir weasyprint==60.2

# Optional BART/XGBoost (skip if install fails — proxy fallback used)
RUN pip install --no-cache-dir pymc-bart==0.11.0 xgboost==3.2.0 || true

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command: run all benchmarks + verify reproduction
CMD ["make", "reproduce"]
