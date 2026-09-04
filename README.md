# DistAI-Docker

Distributed AI inference system with Docker Compose and Kubernetes deployment.

## Quick Start

**Docker Compose:**
```bash
docker-compose up --build
python scripts/test_request.py --mode text --text "hello"
```

**Kubernetes:**
```bash
kubectl apply -f k8s/distai-all-in-one.yaml
kubectl port-forward -n distai svc/coordinator 8000:8000
```

## System Design

Three worker services (BERT, MobileNet, CLIP) handle different input types. Coordinator routes requests intelligently:
- Text → BERT (100-200ms)
- Image → MobileNet (80-150ms)  
- Both → CLIP (150-300ms)

## Features

- Exponential backoff retry (3 attempts, <3.5s max)
- Health checks every 5 seconds
- Prometheus metrics and structured logging
- Docker Compose for development
- Kubernetes for production (19 resources: Deployments, Services, HPA, NetworkPolicy, RBAC)
- 25+ unit tests, >80% coverage

## Usage

Send requests:
```bash
# Text
python scripts/test_request.py --mode text --text "test"

# Image  
python scripts/test_request.py --mode image --image_url "https://picsum.photos/256"

# Both
python scripts/test_request.py --mode both --text "cat" --image_url "https://picsum.photos/256"
```

Check status:
```bash
curl http://localhost:8000/status
curl http://localhost:8000/metrics
```

Run tests:
```bash
docker-compose exec coordinator python /scripts/test_batch.py
pytest tests/test_coordinator.py -v
```

## API

**POST /infer**
```json
{"text": "...", "image_base64": "..."}
```
Returns result + latency + request_id. Errors: 400 (bad input), 503 (worker offline), 504 (retries failed).

**GET /status** - System health and request logs  
**GET /metrics** - Prometheus metrics  
**GET /health** - Health check

## Deployment

| Feature | Docker Compose | Kubernetes |
|---------|---|---|
| Setup | < 5 min | 15-30 min |
| Scaling | Manual | Auto (HPA) |
| Failover | No | Yes (< 30s) |
| Zero-downtime updates | No | Yes |
| Network isolation | No | Yes |

## Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) - Design and trade-offs
- [K8S_MIGRATION.md](K8S_MIGRATION.md) - Kubernetes guide
- [COMPOSE_VS_K8S.md](COMPOSE_VS_K8S.md) - Technology comparison

## Testing

```bash
# Unit tests
pytest tests/test_coordinator.py -v

# Integration
docker-compose exec coordinator python /scripts/test_batch.py

# Validation  
python validate_logic.py
```

## Project Structure

```
coordinator/      - Routing service
workers/          - BERT, MobileNet, CLIP
k8s/              - Kubernetes manifests
tests/            - 25+ unit tests
scripts/          - Test utilities
docker-compose.yml
```

## Performance

- Average latency: ~160ms
- P99: <250ms
- Success rate: 100%
- Throughput: ~6 req/sec (single-threaded)

Kubernetes scales 2-10 replicas under load.
