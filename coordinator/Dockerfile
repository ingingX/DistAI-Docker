# Dockerfile for Coordinator
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    # delete apt cache to reduce image size
    && rm -rf /var/lib/apt/lists/* 

# Copy requirements first for better caching
COPY coordinator/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy coordinator source code
COPY coordinator/ .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the coordinator
CMD ["python", "coordinator.py"]