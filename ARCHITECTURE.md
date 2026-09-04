# Architecture Documentation

## System Overview

DistAI-Docker is a containerized microservices architecture for distributed AI model inference. It demonstrates core patterns in production ML systems: service discovery, intelligent routing, fault tolerance, and observability.

```
┌─────────────────────────────────────────────────────────────┐
│                  Coordinator Service                         │
│                    (Port 8000)                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Request Router (intelligent routing by modality)  │   │
│  │ • Health Monitor (periodic checks, 5s interval)     │   │
│  │ • Retry Handler (exponential backoff, max 3)        │   │
│  │ • Request Logger (structured logs, last 50)         │   │
│  │ • Metrics Exporter (Prometheus integration)         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │              │              │
    ┌────▼───┐      ┌────▼────┐     ┌─▼────────┐
    │ BERT   │      │MobileNet │    │  CLIP    │
    │Worker1 │      │ Worker2  │    │ Worker3  │
    │(9001)  │      │ (9002)   │    │ (9003)   │
    └────────┘      └──────────┘    └──────────┘
```

## Components

### 1. Coordinator Service
**Role**: Central intelligence for request routing and orchestration

**Key Responsibilities**:
- **Input Validation & Routing**: Determines target worker based on input modality
- **Health Monitoring**: Periodic checks every 5 seconds to track worker availability
- **Fault Tolerance**: Retry logic with exponential backoff for transient failures
- **Observability**: Structured logging and Prometheus metrics export
- **State Management**: Maintains worker registry and request history

**Configuration**:
```python
MAX_RETRIES = 3                    # Maximum retry attempts per request
RETRY_BACKOFF = 0.5               # Base backoff in seconds (exponential)
HEALTH_CHECK_INTERVAL = 5         # Health check frequency in seconds
REQUEST_TIMEOUT = 10              # Worker request timeout in seconds
MAX_LOG_SIZE = 50                 # Keep last N requests in memory
```

**Endpoints**:
- `POST /infer` - Main inference endpoint
- `GET /status` - System status and recent logs
- `GET /metrics` - Prometheus metrics (Openmetrics format)
- `GET /health` - Simple health check

### 2. Worker Services
**Role**: Specialized ML model inference containers

Three worker types, each running a specialized model:

#### Worker 1: BERT (Text Analysis)
- **Port**: 9001
- **Model**: `prajjwal1/bert-tiny` (lightweight BERT)
- **Input**: Text only
- **Output**: Embedding sum (scalar)
- **Typical Latency**: 100-200ms
- **Use Case**: Text embedding and encoding

#### Worker 2: MobileNet (Image Classification)
- **Port**: 9002
- **Model**: `torchvision.models.mobilenet_v3_small` (pretrained)
- **Input**: Base64-encoded image
- **Output**: Max logit (scalar)
- **Typical Latency**: 80-150ms
- **Use Case**: Image classification

#### Worker 3: CLIP (Vision-Language)
- **Port**: 9003
- **Model**: `openai/clip-vit-base-patch32` (CLIP ViT-B/32)
- **Input**: Text + Image
- **Output**: Similarity score (scalar)
- **Typical Latency**: 150-300ms
- **Use Case**: Image-text matching and semantic search

## Request Flow

### Typical Request Lifecycle (Text Input)

```
1. Client sends POST /infer with {"text": "..."}
   ↓
2. Coordinator receives request
   ├─ Generate unique request_id
   ├─ Increment active_requests gauge
   ↓
3. Input Validation & Routing
   ├─ Validate text is non-empty string
   ├─ Determine worker_type = BERT
   ↓
4. Health Check
   ├─ Verify worker1 status = ONLINE
   ├─ If offline, return 503 immediately
   ↓
5. Dispatch with Retries (max 3 attempts)
   ├─ Attempt 1: POST to http://worker1:9001/infer
   │  ├─ If success: log and return
   │  └─ If timeout/error: exponential backoff
   ├─ Attempt 2: Wait 0.5s, retry
   │  └─ If timeout/error: exponential backoff 1.0s
   └─ Attempt 3: Wait 1.0s, retry
      └─ If all fail: return 504
   ↓
6. Response Logging
   ├─ Record latency, attempt count, status
   ├─ Maintain recent_requests buffer
   ├─ Update Prometheus metrics
   ↓
7. Return response to client
   ├─ Include result, latency_ms, request_id, attempts
   └─ Decrement active_requests gauge
```

## Routing Logic

| Input Type | Route | Worker | Rationale |
|-----------|-------|--------|-----------|
| Text only | → BERT | worker1:9001 | Specialized text encoder |
| Image only | → MobileNet | worker2:9002 | Optimized for images |
| Both | → CLIP | worker3:9003 | Vision-language model |

### Design Rationale

- **Modality-based routing**: Different models excel at different tasks; route to specialized workers
- **Static routing**: No dynamic load balancing (future enhancement)
- **Single worker per type**: Simplified demo (production would have multiple replicas)

## Error Handling & Resilience

### Failure Modes and Recovery

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Worker timeout | Request timeout (10s) | Retry with exponential backoff |
| Worker HTTP error | Status code ≠ 200 | Retry up to 3 times |
| Worker offline | Health check failure | Return 503 "Worker unavailable" |
| Invalid input | Validation check | Return 400 "Invalid input" |

### Exponential Backoff Strategy

```python
Wait time = RETRY_BACKOFF * (2 ^ attempt_number)

Attempt 1: Fail immediately → Wait 0.5s
Attempt 2: Retry → Wait 1.0s
Attempt 3: Retry → Wait 2.0s
Attempt 4: Fail → Return 504
```

**Rationale**:
- Avoids thundering herd (all clients retrying simultaneously)
- Gives transient failures time to recover
- Bounded backoff (max 3 retries ≈ 3.5s total)

### Health Check Logic

```
Every 5 seconds:
  For each worker:
    - Send GET /status (2s timeout)
    - If response 200: mark ONLINE
    - If timeout/error: mark OFFLINE
    - Update Prometheus gauge
```

**Design Decisions**:
- 5s interval: Balance between fast detection and monitoring overhead
- 2s timeout: Differentiate between slow and unreachable services
- Separate check thread: Non-blocking, independent from request handling

## Observability

### Logging

**Structured Logging** with context:
```
[request_id] Routing text request to worker1
[request_id] Attempt 1: Success after 145ms
[request_id] Failed after 3 attempts: Timeout after 10s
```

### Metrics (Prometheus)

**Counters**:
- `coordinator_requests_total` - Total requests by worker_type and status
- `coordinator_requests_retried_total` - Requests requiring retries
- `coordinator_worker_status` - Worker online/offline status (1/0)

**Histograms**:
- `coordinator_request_latency_seconds` - Request latency distribution

**Gauges**:
- `coordinator_active_requests` - Currently processing requests

### Status Endpoint

Returns JSON with:
- Worker status (online/offline/degraded)
- Last 10 requests
- Performance statistics (success rate, avg latency)

## Design Decisions & Trade-offs

### 1. Flask vs FastAPI
| Aspect | Flask | FastAPI |
|--------|-------|---------|
| Learning Curve | Gentle | Steeper |
| Performance | Single-threaded | Async, high concurrency |
| Code Length | Short | More boilerplate |
| Best For | Learning, small projects | Production, high throughput |

**Decision**: Flask for clarity and demo purposes. Production would migrate to FastAPI.

### 2. In-Memory State
| Approach | Pros | Cons |
|----------|------|------|
| In-memory (current) | Simple, fast access | Lost on restart |
| Database (PostgreSQL) | Persistent, queryable | Added complexity |
| Message queue (Redis) | Distributed, scalable | Infrastructure overhead |

**Decision**: In-memory for demo simplicity. Production would use PostgreSQL for persistence.

### 3. Static Routing
| Approach | Pros | Cons |
|----------|------|------|
| Static (current) | Predictable, simple | Can't rebalance load |
| Dynamic | Load-aware, adaptive | Complex state management |
| Service mesh (Istio) | Automatic, advanced | Steep learning curve |

**Decision**: Static routing for clarity. Production would use dynamic load tracking.

### 4. Single Coordinator
| Approach | Pros | Cons |
|----------|------|------|
| Single (current) | Simple deployment | Single point of failure |
| HA Pair | High availability | More complexity |
| Load-balanced fleet | Horizontal scaling | Infrastructure cost |

**Decision**: Single for simplicity. Production would use load-balanced coordinators.

## Known Limitations

1. **Synchronous Design**
   - Flask uses thread-per-request model
   - Cannot efficiently handle high concurrency
   - Workaround: Use FastAPI with async/await

2. **No Persistence**
   - Request logs lost on restart
   - Worker state not persisted
   - Workaround: Add PostgreSQL + Redis

3. **No Dynamic Load Balancing**
   - Cannot distribute requests among multiple workers of same type
   - Assumes all workers have equal capacity
   - Workaround: Track per-worker load, route to least-loaded

4. **Single Coordinator Instance**
   - Coordinator is single point of failure
   - No failover mechanism
   - Workaround: Use load balancer across multiple coordinators

5. **Limited Monitoring**
   - Basic health checks only
   - No CPU/memory tracking
   - Workaround: Add node exporter, GPU monitoring

## Scalability Path (Future)

### Phase 1: Async Foundation (Minimal effort)
```
Flask → FastAPI + uvicorn
Benefit: 10x throughput, better concurrency
```

### Phase 2: Persistence & Queuing
```
In-memory logs → PostgreSQL
Simple routing → Celery + Redis task queue
Benefit: Durability, distributed processing, fault tolerance
```

### Phase 3: Distributed Deployment
```
1 Coordinator → N Coordinators (load balanced)
1 Worker per type → Multiple replicas per type
Benefit: High availability, horizontal scaling
```

### Phase 4: Advanced Observability
```
Add Jaeger for distributed tracing
Add Prometheus scrape config
Add Grafana dashboards
Benefit: Comprehensive visibility, root cause analysis
```

### Phase 5: Optimization
```
Model quantization (INT8)
Batch inference processing
Caching layer (Redis)
Early exit inference
Benefit: 5-10x latency reduction
```

## Performance Characteristics

### Baseline Metrics (3 test runs, 7 requests each)

| Metric | Value |
|--------|-------|
| Avg Latency | 160ms |
| P99 Latency | 250ms |
| Success Rate | 100% |
| Throughput | ~6 req/s (single coordinator) |

### Bottlenecks
1. **Flask sync I/O**: Single thread blocks on each request
2. **Network latency**: HTTP overhead between coordinator and worker
3. **Model inference**: Worker processing time (bulk of latency)

### Improvement Potential
- FastAPI + uvicorn: 10x throughput (async I/O)
- Batch inference: 3-5x latency reduction
- Model quantization: 2-3x speed improvement
- caching: 100x+ for cache hits

## Testing Strategy

### Unit Tests (`tests/test_coordinator.py`)
- Input validation (valid/invalid combinations)
- Routing logic (text→BERT, image→MobileNet, both→CLIP)
- Error handling (400, 503, 504 responses)
- Metrics collection

### Integration Tests
- Full request flow with real workers
- Retry behavior under simulated failures
- Worker recovery after temporary outage

### Load Tests
- Run `test_batch.py`: 21 sequential requests
- Measure throughput and latency distribution

## Running Tests

```bash
# Unit tests
pytest tests/test_coordinator.py -v

# Integration test
docker-compose exec coordinator python /scripts/test_batch.py

# Check metrics
curl http://localhost:8000/metrics

# Monitor status
curl http://localhost:8000/status | jq
```

## Deployment

### Local (Docker Compose)
```bash
docker-compose up --build
```

### Production Considerations
1. Use Kubernetes for orchestration
2. Add persistent volumes for logs
3. Configure resource limits and requests
4. Add ingress controller for API gateway
5. Enable horizontal pod autoscaling
6. Set up distributed tracing (Jaeger)
7. Add Prometheus scrape targets
8. Configure health probes (liveness, readiness)

## References

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Prometheus Client Library](https://github.com/prometheus/client_python)
- [Distributed Systems Patterns](https://martinfowler.com/articles/patterns-of-distributed-systems/)
- [ML Systems Design](https://stanford-cs329s.github.io/)
