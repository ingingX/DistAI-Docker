# DistAI-Docker

Distributed AI inference system demonstrating production microservices patterns: intelligent request routing, fault tolerance, health monitoring, and observability.

## Overview

DistAI routes inference requests to specialized ML models based on input modality. Three worker services handle text (BERT), image (MobileNet), and vision-language tasks (CLIP). The coordinator dispatches requests with retries, monitors worker health, and exports Prometheus metrics.

```
┌─────────────────────────────────────────┐
│      Coordinator (Port 8000)            │
│  - Route requests by modality           │
│  - Monitor worker health (5s interval)  │
│  - Retry with exponential backoff       │
│  - Prometheus metrics export            │
└────────┬────────────────┬────────────────┘
         │                │
    ┌────▼────┐     ┌────▼────┐     ┌─────────┐
    │  BERT   │     │MobileNet │    │  CLIP   │
    │(9001)   │     │ (9002)   │    │ (9003)  │
    └─────────┘     └──────────┘    └─────────┘
```

## Quick Start

**Docker Compose (development):**
```bash
docker-compose up --build
python scripts/test_request.py --mode text --text "hello"
```

**Kubernetes (production):**
```bash
kubectl apply -f k8s/distai-all-in-one.yaml
kubectl port-forward -n distai svc/coordinator 8000:8000
```

## Architecture

### Request Routing

Requests are routed based on input modality:

| Input | Worker | Model | Port | Latency |
|-------|--------|-------|------|---------|
| Text only | BERT | prajjwal1/bert-tiny | 9001 | 100-200ms |
| Image only | MobileNet | torchvision MobileNetV3 | 9002 | 80-150ms |
| Text + Image | CLIP | openai/clip-vit-base-patch32 | 9003 | 150-300ms |

### Fault Tolerance

- **Health monitoring**: Background thread checks worker health every 5 seconds
- **Retry logic**: Exponential backoff (0.5s, 1.0s, 2.0s) up to 3 attempts
- **Request timeout**: 10 second timeout per attempt
- **HTTP status codes**: 400 (bad input), 503 (worker offline), 504 (retries exhausted)

### Observability

**Prometheus metrics** (`/metrics` endpoint):
- `coordinator_requests_total` - Total requests by worker type and status
- `coordinator_requests_retried_total` - Requests requiring retries
- `coordinator_request_latency_seconds` - Latency histogram
- `coordinator_worker_status` - Worker online/offline
- `coordinator_active_requests` - Currently processing

**Status endpoint** (`/status`):
- Worker status and availability
- Last 10 requests with latency
- Performance statistics

## API

**POST /infer**
```json
{
  "text": "example text (optional)",
  "image_base64": "base64-encoded image (optional)"
}
```

Response:
```json
{
  "result": 0.523,
  "latency_ms": 145,
  "request_id": "req-12345",
  "attempts": 1
}
```

**GET /status** - System health and recent request logs  
**GET /metrics** - Prometheus metrics (OpenMetrics format)  
**GET /health** - Simple health check for load balancers

## Testing

```bash
# Unit tests
pytest tests/test_coordinator.py -v

# Integration test
docker-compose exec coordinator python /scripts/test_batch.py

# Standalone validation (no Docker needed)
python3 validate_logic.py
```

25+ unit tests cover input validation, routing logic, error handling, and metrics collection.

## Performance

- Average latency: ~160ms
- P99 latency: <250ms
- Success rate: 100%
- Throughput: ~6 req/s (single-threaded coordinator)

Kubernetes HPA scales workers 2-10 replicas under load.

## Deployment

### Docker Compose
```bash
docker-compose up --build
```

Setup: <5 min  
Scaling: Manual  
Failover: No  

### Kubernetes
```bash
kubectl apply -f k8s/distai-all-in-one.yaml
```

Setup: 15-30 min  
Scaling: Automatic HPA (CPU >70%, Memory >80%)  
Failover: Yes (<30s recovery)  
Zero-downtime updates: Yes (RollingUpdate)  
Network isolation: Yes (NetworkPolicy)

K8s manifest includes: Deployments, Services, HPA, RBAC, NetworkPolicy, ConfigMap, readiness/liveness probes, graceful shutdown hooks.

## Project Structure

```
coordinator/          - Router, health monitor, metrics
workers/              - BERT, MobileNet, CLIP services
k8s/                  - Kubernetes manifests (production-ready)
tests/                - 25+ unit tests
scripts/              - Integration test utilities
docker-compose.yml    - Local development setup
```

## Design Decisions

**Flask vs FastAPI**: Flask chosen for clarity in a learning project. Production would use FastAPI for async/await and higher concurrency.

**In-memory state vs Database**: In-memory for simplicity. Production would use PostgreSQL for persistence and queryability.

**Static routing vs Dynamic load balancing**: Static routing for predictability. Production would track per-worker load and route adaptively.

**Single coordinator vs HA pair**: Single instance for simplicity. Production would load-balance across multiple coordinator instances.

**Known limitations**: Synchronous Flask design limits concurrency; no request log persistence; no dynamic load balancing; single coordinator is a failure point; basic health checks only.

## Documentation

- **ARCHITECTURE.md** - System design, request flow, error handling, scalability path
- **K8S_MIGRATION.md** - Kubernetes deployment guide
- **COMPOSE_VS_K8S.md** - Technology comparison
- **IMPROVEMENTS.md** - Engineering practices demonstrated

## Production Readiness

The codebase demonstrates:
- Request routing and service discovery
- Retry logic with exponential backoff
- Health monitoring and failure detection
- Structured logging with request tracing
- Prometheus metrics integration
- Comprehensive unit tests (>80% coverage)
- Kubernetes manifests with HPA, RBAC, NetworkPolicy
- Graceful degradation and error handling

Clear scaling path documented: async foundation (FastAPI) → persistence & queuing (PostgreSQL, Redis) → advanced observability (Jaeger, Grafana) → optimization (quantization, batching, caching).
