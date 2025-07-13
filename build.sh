#!/bin/bash
# build.sh - Build all Docker images

echo "Building Docker images..."

# Build coordinator
echo "Building coordinator..."
docker build -t ai-inference-coordinator -f coordinator/Dockerfile .

# Build workers
echo "Building workers..."
docker build -t ai-inference-workers -f workers/Dockerfile .

# Build tester
echo "Building tester..."
docker build -t ai-inference-tester -f tester/Dockerfile .

echo "Build complete!"

# Optional: Start the services
read -p "Do you want to start the services? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting services..."
    docker-compose up -d
    echo "Services started! Check status with: docker-compose ps"
fi