FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY workers/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy workers source code
COPY workers/ .

# Expose port (will be overridden by docker-compose)
EXPOSE 9001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-9001}/health || exit 1

# Default command (will be overridden by docker-compose)
CMD ["python", "w1-BERT.py"]