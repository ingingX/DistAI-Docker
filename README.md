# DistAI-Docker: Distributed AI Inference System

> A containerized microservices architecture for distributed ML model inference, demonstrating core patterns in production AI systems: intelligent request routing, fault tolerance, health monitoring, and observability.

## Quick Start

```bash
# Clone and start services
cd DistAI-Docker
docker-compose up --build

# In another terminal, send test requests
python scripts/test_request.py --api http://localhost:8000/infer --mode text --text "This is a test"
```

## Architecture Overview

The system consists of:
- **1 Coordinator**: Central service for request routing, health monitoring, and observability
- **3 Specialized Workers**: Each running a different ML model optimized for specific tasks

```
┌─────────────────────────────────┐
│     Coordinator (8000)          │
│  • Request Router               │
│  • Health Monitor               │
│  • Retry Handler                │
│  • Metrics Exporter             │
└─────────────────────────────────┘
     │              │              │
  ┌──▼──┐       ┌──▼───┐      ┌──▼──┐
  │BERT │       │Mobile│      │CLIP │
  │W1   │       │Net W2│      │W3   │
  └─────┘       └──────┘      └─────┘
  (9001)        (9002)        (9003)
```

## Request Routing

The coordinator intelligently routes requests based on input modality:

| Input | Worker | Model | Typical Latency |
|-------|--------|-------|-----------------|
| Text only | BERT (W1) | prajjwal1/bert-tiny | 100-200ms |
| Image only | MobileNet (W2) | mobilenet_v3_small | 80-150ms |
| Text + Image | CLIP (W3) | clip-vit-base-patch32 | 150-300ms |

## Usage

### 1. Start the System

```bash
docker-compose up --build
```

Wait for all services to start (health checks complete in ~10 seconds).

### 2. Send Requests

**From host machine:**
```bash
# Text-only inference (BERT)
python scripts/test_request.py --api http://localhost:8000/infer \
  --mode text --text "This is a test sentence"

# Image-only inference (MobileNet)
python scripts/test_request.py --api http://localhost:8000/infer \
  --mode image --image_url "https://picsum.photos/256"

# Combined inference (CLIP)
python scripts/test_request.py --api http://localhost:8000/infer \
  --mode both --text "a cat" --image_url "https://picsum.photos/256"
```

**From Docker container:**
```bash
docker-compose exec coordinator python /scripts/test_request.py --mode text --text "test"
docker-compose exec coordinator python /scripts/test_request.py --mode image --image_url "https://picsum.photos/256"
docker-compose exec coordinator python /scripts/test_request.py --mode both --text "a cat" --image_url "https://picsum.photos/256"
```

### 3. Run Batch Tests

```bash
docker-compose exec coordinator python /scripts/test_batch.py
```

This sends 21 sequential requests (7 text + 7 image + 7 combined).

### 4. Monitor System Status

```bash
# System status and recent request logs
curl http://localhost:8000/status | jq

# Prometheus metrics
curl http://localhost:8000/metrics

# Simple health check
curl http://localhost:8000/health
```

## API Endpoints

### POST /infer

**Request body:**
```json
{
  "text": "optional text input",
  "image_base64": "optional base64 encoded image"
}
```

**Response (success):**
```json
{
  "result": <model_output>,
  "worker_id": "worker_x",
  "latency_ms": 145.2,
  "request_id": 123456,
  "attempts": 1,
  "timestamp": "2024-01-15T10:30:45.123456"
}
```

**Response (error):**
```json
{
  "error": "error description",
  "request_id": 123456
}
```

**Status codes:**
- `200`: Success
- `400`: Invalid input (no text or image provided)
- `503`: Worker unavailable
- `504`: All retry attempts exhausted

### GET /status

Returns system status including:
- Worker status (online/offline)
- Recent request logs (last 10)
- Performance statistics (success rate, avg latency)

**Response:**
```json
{
  "coordinator": "online",
  "timestamp": "2024-01-15T10:30:45.123456",
  "workers": {
    "bert": {"id": "worker1", "status": "online", ...},
    ...
  },
  "recent_requests": [...],
  "stats": {
    "total_requests": 42,
    "successful_requests": 42,
    "failed_requests": 0,
    "success_rate": 1.0,
    "avg_latency_ms": 158.3
  }
}
```

### GET /metrics

Prometheus metrics endpoint. Exposes:
- `coordinator_requests_total` - Total requests by type and status
- `coordinator_requests_retried_total` - Requests requiring retries
- `coordinator_request_latency_seconds` - Latency histogram
- `coordinator_worker_status` - Worker online status (1/0)
- `coordinator_active_requests` - Currently processing requests

### GET /health

Simple health check for load balancers.

**Response:**
```json
{"status": "ok"}
```

## Fault Tolerance

### Retry Strategy

Requests automatically retry on transient failures using **exponential backoff**:

```
Attempt 1: Fail immediately
Wait 0.5s
Attempt 2: Retry
Wait 1.0s
Attempt 3: Retry
Wait 2.0s
Attempt 4: Fail → Return 504
```

**Total max time: ~3.5 seconds per request**

### Health Monitoring

The coordinator performs health checks every 5 seconds:
- Sends `GET /status` to each worker
- Updates worker status (online/offline)
- Immediately returns 503 if target worker is offline
- No request waits for health check completion

### Failure Modes

| Scenario | Response | Recovery |
|----------|----------|----------|
| Worker timeout | Retry with backoff | Worker recovers (health check detects) |
| Network error | Retry with backoff | Automatic retry works |
| Worker offline | Return 503 immediately | Detected by next health check |
| Invalid input | Return 400 immediately | Client must fix request |

## Testing

### Unit Tests

```bash
# Run unit tests with coverage
pytest tests/test_coordinator.py -v

# Or use the helper script
./run_tests.sh
```

Tests cover:
- Input validation (valid/invalid combinations)
- Routing logic (correct worker selection)
- Error handling (400, 503, 504 responses)
- Endpoint functionality
- Worker registry configuration
- Retry mechanism
- Metrics collection

### Integration Tests

```bash
docker-compose exec coordinator python /scripts/test_batch.py
```

Sends 21 requests and measures:
- Response times
- Success rate
- Error handling

## Design Decisions

### Why Flask?
- Lightweight and easy to understand
- Suitable for demonstrating core concepts
- Production systems would use **FastAPI** for:
  - Async/await support → 10x throughput
  - Better concurrency handling
  - Type validation via Pydantic

### Why Simple Routing?
- Current: Static routing based on input type
- Production would add:
  - Dynamic load tracking
  - Multiple worker replicas per type
  - Least-loaded worker selection

### Why In-Memory State?
- Current: Request logs stored in memory
- Production would add:
  - PostgreSQL for persistence
  - Redis for distributed state
  - Kafka for event streaming

### Why Single Coordinator?
- Current: Single instance
- Production would deploy:
  - Load-balanced coordinator fleet
  - Shared state (Redis)
  - Automatic failover

## Configuration

Edit `coordinator/coordinator.py` to adjust:

```python
MAX_RETRIES = 3                    # Max retry attempts
RETRY_BACKOFF = 0.5               # Base backoff (exponential)
HEALTH_CHECK_INTERVAL = 5         # Health check frequency (seconds)
REQUEST_TIMEOUT = 10              # Worker request timeout (seconds)
MAX_LOG_SIZE = 50                 # Keep last N requests
```

## Performance Metrics

Based on integration tests (21 sequential requests):

| Metric | Value |
|--------|-------|
| Average Latency | ~160ms |
| P99 Latency | ~250ms |
| Success Rate | 100% |
| Throughput | ~6 req/s (limited by single Flask thread) |

**Bottleneck**: Flask sync I/O (single thread). FastAPI + uvicorn would achieve 10x throughput.

## Deployment

### Local Development
```bash
docker-compose up --build
```

### Production Deployment

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed guidance on:
- Kubernetes deployment
- Multi-coordinator setup
- Distributed tracing (Jaeger)
- Prometheus monitoring
- Horizontal scaling
- Resource limits

## Project Structure

```
DistAI-Docker/
├── coordinator/
│   ├── coordinator.py          # Main coordinator service
│   ├── Dockerfile              # Container image
│   └── requirements.txt         # Python dependencies
├── workers/
│   ├── w1-BERT.py              # BERT worker service
│   ├── w2-MobileNet.py         # MobileNet worker service
│   ├── w3-CLIP.py              # CLIP worker service
│   ├── Dockerfile              # Shared worker image
│   └── requirements.txt         # Worker dependencies
├── scripts/
│   ├── test_request.py         # Single request test script
│   └── test_batch.py           # Batch test (21 requests)
├── tests/
│   ├── test_coordinator.py     # Unit tests
│   ├── conftest.py             # Pytest configuration
│   └── requirements.txt         # Test dependencies
├── docker-compose.yml          # Service orchestration
├── ARCHITECTURE.md             # Detailed design documentation
├── README.md                   # This file
└── run_tests.sh               # Test runner script
```

## Key Learnings

This project demonstrates:

✓ **Service-oriented architecture** - Separate services with clear responsibilities
✓ **Intelligent request routing** - Content-aware dispatch to specialized workers
✓ **Fault tolerance patterns** - Retry logic with exponential backoff
✓ **Health monitoring** - Periodic checks and status tracking
✓ **Observability** - Structured logging and Prometheus metrics
✓ **Container orchestration** - Docker Compose for local deployment
✓ **API design** - RESTful endpoints with proper HTTP semantics

## Future Enhancements

1. **Async I/O** → FastAPI + uvicorn (10x throughput)
2. **Persistence** → PostgreSQL + Redis (durability)
3. **Scaling** → Multiple coordinator and worker replicas
4. **Advanced monitoring** → Jaeger tracing, Grafana dashboards
5. **Optimization** → Model quantization, batch processing, caching
6. **Kubernetes** → Native K8s deployment instead of Docker Compose

## Running with Docker Compose

```bash
# Start services (first time will download images)
docker-compose up --build

# View logs
docker-compose logs -f coordinator

# Run tests
docker-compose exec coordinator python /scripts/test_batch.py

# Stop services
docker-compose down

# Clean up volumes
docker-compose down -v
```

## License

This project is provided as-is for educational and demonstration purposes.

## References

- [Distributed Systems Design Patterns](https://martinfowler.com/articles/patterns-of-distributed-systems/)
- [ML Systems Design](https://stanford-cs329s.github.io/)
- [Microservices Patterns](https://microservices.io/)
- See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed references
