# DistAI-Docker: Distributed AI Inference System

> Production-grade containerized microservices for distributed ML inference. Demonstrates intelligent routing, fault tolerance, observability, and multi-environment deployment.

## 🚀 Quick Start

### Docker Compose (Development)
```bash
cd DistAI-Docker
docker-compose up --build

# Test
python scripts/test_request.py --api http://localhost:8000/infer \
  --mode text --text "This is a test"
```

### Kubernetes (Production)
```bash
# Prerequisites: kubectl, K8s cluster (minikube/EKS/GKE/AKS)
kubectl apply -f k8s/distai-all-in-one.yaml
kubectl get pods -n distai -w
kubectl port-forward -n distai svc/coordinator 8000:8000
```

---

## 📊 Architecture

```
┌──────────────────────────────────────────┐
│    Coordinator (Request Router)          │
│  • Intelligent routing by modality       │
│  • Health monitoring (5s)                │
│  • Exponential backoff retry (3 times)   │
│  • Prometheus metrics                    │
└──────────────────────────────────────────┘
     │              │              │
  ┌──▼──┐      ┌──▼────┐      ┌──▼────┐
  │BERT │      │Mobile │      │ CLIP  │
  │ W1  │      │Net W2 │      │ W3    │
  │9001 │      │ 9002  │      │ 9003  │
  └─────┘      └───────┘      └───────┘
```

| Input | Route | Model | Latency |
|-------|-------|-------|---------|
| Text | → BERT | prajjwal1/bert-tiny | ~100-200ms |
| Image | → MobileNet | mobilenet_v3_small | ~80-150ms |
| Both | → CLIP | clip-vit-base-patch32 | ~150-300ms |

---

## 📖 Usage

### Send Requests

**Text (BERT):**
```bash
python scripts/test_request.py --mode text --text "Your text here"
```

**Image (MobileNet):**
```bash
python scripts/test_request.py --mode image --image_url "https://picsum.photos/256"
```

**Both (CLIP):**
```bash
python scripts/test_request.py --mode both --text "a cat" --image_url "https://picsum.photos/256"
```

### Run Tests
```bash
# Batch test (21 requests)
docker-compose exec coordinator python /scripts/test_batch.py

# Unit tests
pytest tests/test_coordinator.py -v
```

### Monitor Status
```bash
curl http://localhost:8000/status | jq
curl http://localhost:8000/metrics
```

---

## 🔧 API Endpoints

- `POST /infer` - Main inference endpoint
  - Input: `{"text": "...", "image_base64": "..."}`
  - Returns: Result + latency + request_id
  - Errors: 400 (bad input), 503 (worker offline), 504 (retries exhausted)

- `GET /status` - System status and recent requests

- `GET /metrics` - Prometheus metrics

- `GET /health` - Simple health check

---

## ✨ Key Features

- ✅ **Intelligent Routing** - Modality-based worker selection
- ✅ **Fault Tolerance** - Exponential backoff (3 retries, <3.5s max)
- ✅ **Health Monitoring** - 5-second checks, auto-recovery
- ✅ **Observability** - Prometheus metrics + structured logging
- ✅ **Docker & K8s** - Works in both environments
- ✅ **Auto-Scaling** - K8s HPA: 2-10 replicas based on CPU
- ✅ **Zero-Downtime** - K8s rolling updates
- ✅ **Security** - K8s NetworkPolicy + RBAC
- ✅ **Testing** - 25+ unit tests, integration tests

---

## 📊 Deployment Comparison

| Feature | Docker Compose | Kubernetes |
|---------|---|---|
| Setup | < 5 min | 15-30 min |
| Scaling | ✗ Manual | ✓ Auto (HPA) |
| Auto-restart | ⚠️ Limited | ✓ Full |
| Node failure | ✗ Down | ✓ Auto-migrate (< 30s) |
| Zero-downtime updates | ✗ No | ✓ Yes |
| Network isolation | ✗ No | ✓ Yes |
| Production ready | ⚠️ Partial | ✓ Yes |

---

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design, trade-offs, decisions
- **[K8S_MIGRATION.md](K8S_MIGRATION.md)** - Kubernetes deployment guide
- **[K8S_QUICKSTART.md](K8S_QUICKSTART.md)** - kubectl cheatsheet
- **[COMPOSE_VS_K8S.md](COMPOSE_VS_K8S.md)** - Technology comparison
- **[IMPROVEMENTS.md](IMPROVEMENTS.md)** - Project improvements

---

## 🏗️ Project Structure

```
DistAI-Docker/
├── coordinator/          # Central routing service
├── workers/              # BERT, MobileNet, CLIP workers
├── k8s/                  # Kubernetes manifests (19 resources)
├── scripts/              # Test scripts
├── tests/                # Unit tests (25+)
├── docker-compose.yml    # Development setup
└── README.md             # This file
```

---

## 🎯 Design Highlights

**Exponential Backoff:** Retries with 0.5s → 1.0s → 2.0s waits to prevent thundering herd

**Three Workers:** Specialized for different modalities (text, image, multimodal) for optimized performance

**Both Deployments:** Understand trade-offs between simplicity (Docker) and capability (Kubernetes)

**Complete K8s Manifests:** Production-ready with 19 resources, health checks, auto-scaling, network policies

---

## ⚡ Performance

**Baseline (21 sequential requests):**
- Average latency: ~160ms
- P99 latency: <250ms
- Success rate: 100%
- Throughput: ~6 req/sec (single-threaded)

**Scaling potential:**
- Docker Compose: Fixed resources
- Kubernetes: Auto-scales 2-10 replicas under load

---

## 🧪 Testing

```bash
# Unit tests (25+)
pytest tests/test_coordinator.py -v

# Integration test
docker-compose exec coordinator python /scripts/test_batch.py

# Validation (no deps)
python validate_logic.py
```

Test coverage: >80% (routing, validation, error handling, metrics)

---

## 🚀 Next Steps

1. **Run Docker Compose** - `docker-compose up --build`
2. **Send requests** - Test the inference endpoints
3. **Review architecture** - Read [ARCHITECTURE.md](ARCHITECTURE.md)
4. **Deploy to K8s** - `kubectl apply -f k8s/distai-all-in-one.yaml`
5. **Understand trade-offs** - Read [COMPOSE_VS_K8S.md](COMPOSE_VS_K8S.md)

---

## 📝 License

Educational and demonstration purposes.

---

## 🔗 References

- [Distributed Systems Patterns](https://martinfowler.com/articles/patterns-of-distributed-systems/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [ML Systems Design](https://stanford-cs329s.github.io/)
