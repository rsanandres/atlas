FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg2 and general build
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies (CPU-only torch via extra-index-url)
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Create non-root user early so downloads go to accessible locations
RUN groupadd -r appuser && useradd -r -g appuser -m appuser

# Pre-download cross-encoder model to shared cache accessible by appuser
ENV HF_HOME=/app/.cache/huggingface
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('sentence-transformers/all-MiniLM-L6-v2')" && \
    chmod -R a+r /app/.cache

# Pre-download NLTK punkt tokenizer to shared location accessible by appuser
RUN python -c "import nltk; nltk.download('punkt', download_dir='/usr/local/nltk_data', quiet=True); nltk.download('punkt_tab', download_dir='/usr/local/nltk_data', quiet=True)"

# Download RDS CA bundle for SSL certificate verification
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -sS -o /app/rds-combined-ca-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem && \
    apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy application code (only what's needed at runtime)
COPY api/ ./api/
COPY utils/ ./utils/
COPY postgres/queue_storage.py ./postgres/queue_storage.py

# postgres/ needs to be a package for imports
RUN touch ./postgres/__init__.py

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

# Single worker — ECS task gets 0.5 vCPU
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
