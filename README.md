# DistAI-Docker: Distributed AI Inference System

> A production-grade containerized microservices architecture for distributed ML model inference. Demonstrates core patterns in modern AI systems: intelligent request routing, fault tolerance, health monitoring, observability, and multi-environment deployment.

## 🚀 Quick Start

### Option 1: Docker Compose (Development / Local Testing)

```bash
cd DistAI-Docker
docker-compose up --build

# In another terminal, send test requests
python scripts/test_request.py --api http://localhost:8000/infer \
  --mode text --text "This is a test"
```

### Option 2: Kubernetes (Production / Cloud Deployment)

```bash
# Prerequisites: kubectl installed, K8s cluster available (minikube/EKS/GKE/AKS)

# Deploy all services (one command)
kubectl apply -f k8s/distai-all-in-one.yaml

# Wait for pods to be ready
kubectl get pods -n distai -w

# Port forward for testing
kubectl port-forward -n distai svc/coordinator 8000:8000

# Send test requests
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"text": "hello world"}'
```

---

## 📊 System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│                 Coordinator Service                      │
│         Central Request Router & Orchestrator             │
│  • Intelligent routing (text→BERT, image→MobileNet, etc) │
│  • 5-second health monitoring                            │
│  • Exponential backoff retry (3 attempts, <3.5s)         │
│  • Prometheus metrics & structured logging              │
└─────────────────────────────────────────────────────────┘
     │                    │                    │
  ┌──▼──────┐        ┌──▼────────┐       ┌──▼────────┐
  │  BERT   │        │ MobileNet  │       │   CLIP    │
  │ Worker1 │        │ Worker2    │       │ Worker3   │
  │(9001)   │        │(9002)      │       │(9003)     │
  └─────────┘        └────────────┘       └───────────┘
```

### Request Routing

| Input | Route | Model | Latency |
|-------|-------|-------|---------|
| Text only | → BERT Worker | prajjwal1/bert-tiny | ~100-200ms |
| Image only | → MobileNet Worker | mobilenet_v3_small | ~80-150ms |
| Text + Image | → CLIP Worker | clip-vit-base-patch32 | ~150-300ms |

---

## 📋 Deployment Guide

### Docker Compose (Single Machine)

**Best for:** Local development, testing, demonstrations

```bash
# Start services
docker-compose up --build

# View logs
docker-compose logs -f coordinator

# Stop services
docker-compose down
```

**Features:**
- ✓ Simple, one-file configuration
- ✓ Fast startup (< 10 seconds)
- ✗ Single machine only
- ✗ No automatic failover
- ✗ No auto-scaling

### Kubernetes (Multi-Machine / Cloud)

**Best for:** Production, high availability, auto-scaling

#### 1. Local Testing (minikube)

```bash
# Install minikube (if not installed)
brew install minikube  # macOS
# or download from https://minikube.sigs.k8s.io/

# Start minikube
minikube start --cpus=4 --memory=8192

# Build and load images into minikube
docker build -t distai-coordinator:latest ./coordinator
minikube image load distai-coordinator:latest

# ... repeat for other images ...

# Deploy
kubectl apply -f k8s/distai-all-in-one.yaml

# Test
kubectl port-forward -n distai svc/coordinator 8000:8000
curl -X POST http://localhost:8000/infer -H "Content-Type: application/json" -d '{"text": "test"}'
```

#### 2. Cloud Deployment (AWS EKS / GCP GKE / Azure AKS)

All three cloud platforms use the **same manifests**:

```bash
# AWS EKS
aws eks create-cluster --name distai
aws eks update-kubeconfig --name distai
kubectl apply -f k8s/distai-all-in-one.yaml

# Google Cloud GKE
gcloud container clusters create distai
gcloud container clusters get-credentials distai
kubectl apply -f k8s/distai-all-in-one.yaml

# Azure AKS
az aks create -n distai -g myResourceGroup
az aks get-credentials -n distai -g myResourceGroup
kubectl apply -f k8s/distai-all-in-one.yaml
```

**Kubernetes Features:**
- ✓ Multi-node high availability
- ✓ Automatic pod restart (< 1 second)
- ✓ Node failure auto-recovery (< 30 seconds)
- ✓ HPA auto-scaling (2-10 replicas based on CPU)
- ✓ Zero-downtime rolling updates
- ✓ Network policies & RBAC security
- ✓ Prometheus monitoring & alerts

---

## 📖 Usage Examples

### 1. Send Inference Requests

**Text-only (routes to BERT Worker):**
```bash
python scripts/test_request.py --api http://localhost:8000/infer \
  --mode text --text "This is a test sentence"
```

**Image-only (routes to MobileNet Worker):**
```bash
python scripts/test_request.py --api http://localhost:8000/infer \
  --mode image --image_url "https://picsum.photos/256"
```

**Combined (routes to CLIP Worker):**
```bash
python scripts/test_request.py --api http://localhost:8000/infer \
  --mode both --text "a cat" --image_url "https://picsum.photos/256"
```

### 2. Run Integration Tests

**Docker Compose:**
```bash
docker-compose exec coordinator python /scripts/test_batch.py
```

**Kubernetes:**
```bash
kubectl exec -n distai deployment/coordinator -- python /scripts/test_batch.py
```

Sends 21 requests (7 text + 7 image + 7 combined) and measures latency.

### 3. Monitor System Status

**Docker Compose:**
```bash
curl http://localhost:8000/status | jq
curl http://localhost:8000/metrics
```

**Kubernetes:**
```bash
kubectl get pods -n distai
kubectl logs -n distai -l app=coordinator -f
kubectl top pods -n distai  # Resource usage
kubectl describe pod <pod-name> -n distai
```

### 4. Kubernetes-Specific Operations

```bash
# View HPA (auto-scaling) status
kubectl get hpa -n distai

# Scale manually
kubectl scale deployment bert-worker --replicas=5 -n distai

# Update to new image version
kubectl set image deployment/coordinator \
  coordinator=distai-coordinator:v2 -n distai

# Rollback if needed
kubectl rollout undo deployment/coordinator -n distai

# View events
kubectl get events -n distai --sort-by='.lastTimestamp'
```

---

## 🔧 API Endpoints

### POST /infer
Main inference endpoint. Routes request based on input modality.

**Request body:**
```json
{
  "text": "optional text input",
  "image_base64": "optional base64 encoded image"
}
```

**Response (success - 200):**
```json
{
  "result": {"embedding_sum": 123.45},
  "worker_id": "worker1",
  "latency_ms": 145.2,
  "request_id": 123456,
  "attempts": 1,
  "timestamp": "2024-01-15T10:30:45.123456"
}
```

**Error responses:**
- `400`: Invalid input (no text or image provided)
- `503`: Worker unavailable (offline or unhealthy)
- `504`: All retry attempts exhausted

### GET /status
System status and recent request history.

**Response:**
```json
{
  "coordinator": "online",
  "workers": {
    "bert": {"id": "worker1", "status": "online", ...},
    "mobilenet": {"id": "worker2", "status": "online", ...},
    "clip": {"id": "worker3", "status": "online", ...}
  },
  "recent_requests": [...],
  "stats": {
    "total_requests": 42,
    "successful_requests": 42,
    "success_rate": 1.0,
    "avg_latency_ms": 158.3
  }
}
```

### GET /metrics
Prometheus metrics endpoint. For monitoring integration.

### GET /health
Simple health check for load balancers.

---

## 🛡️ Fault Tolerance & Reliability

### Retry Strategy

Coordinator implements **exponential backoff** with max 3 retries:
- Attempt 1: Immediate
- Attempt 2: Wait 0.5s, retry
- Attempt 3: Wait 1.0s, retry
- Attempt 4: Wait 2.0s, fail with 504

**Total maximum time:** < 3.5 seconds per request

### Health Monitoring

**Coordinator:** Checks each Worker every 5 seconds
- Healthy (online) → Accept requests
- Unhealthy (offline) → Return 503 immediately

**Kubernetes:** Additional auto-recovery
- Pod crashes → Automatic restart (< 1 second)
- Node crashes → Auto-migrate Pod to other nodes (< 30 seconds)
- Health checks: Readiness + Liveness + Startup probes

### High Availability

**Docker Compose:** ⚠️ Single point of failure
- If host crashes → entire system down
- Manual recovery required

**Kubernetes:** ✅ Automatic failover
- Pod anti-affinity → Replicas on different nodes
- Multiple replicas → Continuous service
- Auto-scaling → More replicas under load

---

## 📊 Performance

### Baseline Metrics (Integration Tests)

From running `test_batch.py` (21 sequential requests):

| Metric | Value |
|--------|-------|
| Average Latency | ~160ms |
| P99 Latency | <250ms |
| Success Rate | 100% |
| Throughput (single thread) | ~6 req/sec |

### Scaling Potential

| Scenario | Docker Compose | Kubernetes |
|----------|---|---|
| Normal load (10 req/s) | ✓ Works | ✓ Works |
| High load (100 req/s) | ✗ Fails | ✓ Auto-scales to 8 replicas |
| Node failure | ✗ System down | ✓ Auto-recovers (< 30s) |
| Version update | ✗ Downtime | ✓ Zero-downtime rolling update |
| New deployment | Manual | Automated |

---

## 🧪 Testing

### Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/test_coordinator.py -v

# With coverage report
pytest tests/test_coordinator.py --cov=coordinator --cov-report=html
```

**Test coverage:** 25+ tests, >80% code coverage

Includes:
- Input validation (all edge cases)
- Routing logic (text/image/both)
- Error handling (400/503/504)
- Retry mechanism (exponential backoff)
- Metrics collection (Prometheus)

### Integration Tests

**Docker Compose:**
```bash
docker-compose exec coordinator python /scripts/test_batch.py
```

**Kubernetes:**
```bash
kubectl exec -n distai deployment/coordinator -- python /scripts/test_batch.py
```

### Validation (No Dependencies)

```bash
# Verify routing logic and backoff calculation
python validate_logic.py
```

---

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed system design, trade-offs, and decisions
- **[K8S_MIGRATION.md](K8S_MIGRATION.md)** - Complete Kubernetes migration guide with examples
- **[K8S_QUICKSTART.md](K8S_QUICKSTART.md)** - kubectl cheatsheet and quick reference
- **[COMPOSE_VS_K8S.md](COMPOSE_VS_K8S.md)** - Docker Compose vs Kubernetes comparison
- **[IMPROVEMENTS.md](IMPROVEMENTS.md)** - Project improvements summary

---

## 🏗️ Project Structure

```
DistAI-Docker/
├── coordinator/
│   ├── coordinator.py          # Main coordinator service
│   ├── Dockerfile              # Container image
│   └── requirements.txt         # Python dependencies
├── workers/
│   ├── w1-BERT.py              # BERT text encoder
│   ├── w2-MobileNet.py         # MobileNet image classifier
│   ├── w3-CLIP.py              # CLIP vision-language model
│   ├── Dockerfile              # Shared worker image
│   └── requirements.txt         # Python dependencies
├── k8s/
│   └── distai-all-in-one.yaml  # Complete K8s deployment (19 resources)
├── scripts/
│   ├── test_request.py         # Single request test
│   └── test_batch.py           # Batch test (21 requests)
├── tests/
│   ├── test_coordinator.py     # Unit tests (25+)
│   ├── conftest.py             # Pytest configuration
│   └── requirements.txt         # Test dependencies
├── docker-compose.yml          # Local development setup
├── README.md                   # This file
├── ARCHITECTURE.md             # System design details
├── K8S_MIGRATION.md            # K8s deployment guide
├── K8S_QUICKSTART.md           # kubectl quick reference
├── COMPOSE_VS_K8S.md           # Technology comparison
└── IMPROVEMENTS.md             # Improvements summary
```

---

## 🎯 Key Design Decisions

### Why Exponential Backoff?

Instead of immediate retries, we use exponential backoff to:
- Prevent thundering herd (all clients retrying simultaneously)
- Give transient failures time to recover
- Limit total retry time (< 3.5 seconds)

### Why Three Specialized Workers?

Rather than one generic worker:
- **BERT:** Optimized for text processing
- **MobileNet:** Lightweight image classification
- **CLIP:** Efficient multimodal reasoning

Each model is deployed independently, allowing:
- Focused resource optimization
- Independent scaling
- Fault isolation

### Why Both Docker Compose and Kubernetes?

- **Docker Compose:** Quick iteration and local testing
- **Kubernetes:** Production-grade reliability and scalability

This project demonstrates both approaches, helping you understand:
- When each technology is appropriate
- Trade-offs between simplicity and capability
- How to migrate from development to production

---

## 🚀 Deployment Comparison

| Feature | Docker Compose | Kubernetes |
|---------|---|---|
| **Setup time** | < 5 min | 15-30 min |
| **Learning curve** | Easy | Steep |
| **Scalability** | Single machine | Multi-cloud |
| **Auto-scaling** | ✗ No | ✓ Yes |
| **Auto-restart** | ⚠️ Limited | ✓ Full |
| **Zero-downtime updates** | ✗ No | ✓ Yes |
| **Network isolation** | ✗ No | ✓ Yes (NetworkPolicy) |
| **Cost efficiency** | Fixed | Dynamic (pay per use) |
| **Production ready** | ⚠️ Partial | ✓ Yes |

**Recommendation:** Start with Docker Compose for development, graduate to Kubernetes for production.

---

## 📈 Next Steps

### For Learning
- [ ] Run `docker-compose up` to understand the architecture
- [ ] Send requests and observe routing behavior
- [ ] Review [ARCHITECTURE.md](ARCHITECTURE.md) to understand design decisions
- [ ] Read [COMPOSE_VS_K8S.md](COMPOSE_VS_K8S.md) to understand trade-offs

### For Production Deployment
- [ ] Set up a K8s cluster (minikube/EKS/GKE/AKS)
- [ ] Build and push Docker images to a registry
- [ ] Deploy using `kubectl apply -f k8s/distai-all-in-one.yaml`
- [ ] Monitor with Prometheus + Grafana (see [ARCHITECTURE.md](ARCHITECTURE.md))

### For Interview Preparation
- [ ] Deploy both Docker Compose and K8s versions
- [ ] Take screenshots of running systems
- [ ] Prepare talking points on design decisions
- [ ] Practice explaining fault tolerance and scaling

---

## 📞 Key Features Summary

✅ **Intelligent Routing** - Requests routed based on input modality (text→BERT, image→MobileNet, both→CLIP)

✅ **Fault Tolerance** - Exponential backoff retry (3 attempts, <3.5s max)

✅ **Health Monitoring** - 5-second intervals, automatic status updates

✅ **Observability** - Prometheus metrics, structured logging, Request ID tracing

✅ **Containerization** - Docker Compose for development, Kubernetes for production

✅ **Auto-Scaling** - Kubernetes HPA: 2-10 replicas based on CPU/memory

✅ **Zero-Downtime** - Kubernetes RollingUpdate with health checks

✅ **Network Security** - Kubernetes NetworkPolicy for access control

✅ **Testing** - 25+ unit tests, integration tests, validation scripts

✅ **Documentation** - 2,600+ lines of guides and architecture documentation

---

## 📝 License

This project is provided as-is for educational and demonstration purposes.

---

## 🔗 References

- [Distributed Systems Patterns](https://martinfowler.com/articles/patterns-of-distributed-systems/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [ML Systems Design](https://stanford-cs329s.github.io/)
