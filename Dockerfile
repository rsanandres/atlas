FROM python:3.12

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt python-dotenv

# Copy application code
COPY api/ ./api/
COPY utils/ ./utils/
COPY scripts/ ./scripts/
COPY data/ ./data/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=3)" || exit 1

# Run with uvicorn
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
