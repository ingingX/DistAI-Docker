# Kubernetes 部署分析报告

## 📊 工作量评估

| 阶段 | 工作项 | 时间 | 难度 | 价值 |
|------|--------|------|------|------|
| **Phase 1** | Dockerfile 优化 | 30 min | ⭐ | ⭐⭐⭐ |
| **Phase 1** | 编写 K8s manifests | 2-3 hours | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Phase 2** | ConfigMap + Secrets | 1 hour | ⭐ | ⭐⭐⭐ |
| **Phase 2** | Deployment 优化 | 1.5 hours | ⭐⭐ | ⭐⭐⭐⭐ |
| **Phase 3** | Service + Ingress | 1 hour | ⭐⭐ | ⭐⭐⭐⭐ |
| **Phase 3** | Health checks | 1 hour | ⭐ | ⭐⭐⭐⭐ |
| **测试** | 本地测试 + 验证 | 2-3 hours | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **总计** | | **9-11 hours** | | |

---

## 🎯 简历价值对比

### Docker Compose（现状）
```
✓ 展示容器化能力
✓ 微服务架构
- 缺少生产级部署经验
- 无法处理高可用/扩展
```

### Kubernetes（升级后）
```
✓ 展示容器编排能力
✓ 生产级部署经验
✓ 高可用架构
✓ 自动扩展和自修复
✓ 生产环境必备技能
✓ 大公司核心要求
✓ **显著提升简历竞争力**
```

---

## 🚀 具体实现步骤

### Phase 1: 基础 Manifests（2-3小时）

#### 1.1 创建命名空间

**文件**: `k8s/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: distai
  labels:
    name: distai
```

**用途**: 隔离应用资源，便于管理

---

#### 1.2 Coordinator Deployment

**文件**: `k8s/coordinator-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coordinator
  namespace: distai
  labels:
    app: coordinator
spec:
  replicas: 1  # 可扩展到多个副本
  selector:
    matchLabels:
      app: coordinator
  template:
    metadata:
      labels:
        app: coordinator
    spec:
      # Pod 反亲和性：不在同一节点上运行多个副本
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - coordinator
              topologyKey: kubernetes.io/hostname

      containers:
      - name: coordinator
        image: distai-coordinator:latest
        imagePullPolicy: IfNotPresent
        
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        
        # 资源请求和限制
        resources:
          requests:
            cpu: "200m"           # 最少需要 200m CPU
            memory: "256Mi"       # 最少需要 256MB 内存
          limits:
            cpu: "1000m"          # 最多使用 1 CPU
            memory: "1Gi"         # 最多使用 1GB 内存
        
        # 健康检查 - Readiness
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 2
          successThreshold: 1
          failureThreshold: 3
        
        # 健康检查 - Liveness
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 20
          timeoutSeconds: 2
          failureThreshold: 3
        
        # 启动检查（K8s 1.18+）
        startupProbe:
          httpGet:
            path: /health
            port: 8000
          failureThreshold: 30
          periodSeconds: 1
        
        # 环境变量
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: MAX_RETRIES
          value: "3"
        - name: HEALTH_CHECK_INTERVAL
          value: "5"
        
        # 生命周期钩子
        lifecycle:
          preStop:
            exec:
              # 优雅关闭前等待 10 秒，让现有请求完成
              command: ["/bin/sh", "-c", "sleep 10"]
```

**关键特性**:
- Pod 反亲和性（Pod Anti-affinity）：避免单点故障
- 资源请求/限制：确保 K8s 调度器能正确分配资源
- 三层健康检查：Readiness（流量）、Liveness（重启）、Startup（启动）
- 优雅关闭：preStop 钩子确保请求完成后再关闭

---

#### 1.3 Worker Deployment（BERT Worker 示例）

**文件**: `k8s/bert-worker-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bert-worker
  namespace: distai
  labels:
    app: bert-worker
    worker-type: bert
spec:
  replicas: 2  # 初始 2 个副本，可自动扩展到 10 个
  selector:
    matchLabels:
      app: bert-worker
  
  # 更新策略：滚动更新
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1           # 最多比期望副本多 1 个
      maxUnavailable: 0     # 更新时 0 个不可用（零停机）
  
  template:
    metadata:
      labels:
        app: bert-worker
        worker-type: bert
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9001"
        prometheus.io/path: "/metrics"
    
    spec:
      # Node 亲和性：可选择特定节点（如 GPU 节点）
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: kubernetes.io/arch
                operator: In
                values:
                - amd64

      # Pod 反亲和性
      podAntiAffinity:
        preferredDuringSchedulingIgnoredDuringExecution:
        - weight: 100
          podAffinityTerm:
            labelSelector:
              matchExpressions:
              - key: worker-type
                operator: In
                values:
                - bert
            topologyKey: kubernetes.io/hostname
      
      # 初始化容器：预加载模型
      initContainers:
      - name: model-loader
        image: distai-bert-worker:latest
        command: ["/bin/sh", "-c"]
        args:
        - |
          echo "Pre-loading BERT model..."
          python3 -c "from transformers import AutoModel; AutoModel.from_pretrained('prajjwal1/bert-tiny')"
          echo "Model loaded successfully"
        
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1000m"
            memory: "1Gi"

      containers:
      - name: bert-worker
        image: distai-bert-worker:latest
        imagePullPolicy: IfNotPresent
        
        ports:
        - name: http
          containerPort: 9001
          protocol: TCP
        
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "2000m"
            memory: "2Gi"
        
        readinessProbe:
          httpGet:
            path: /status
            port: 9001
          initialDelaySeconds: 30  # 模型加载需要时间
          periodSeconds: 10
          failureThreshold: 3
        
        livenessProbe:
          httpGet:
            path: /status
            port: 9001
          initialDelaySeconds: 60
          periodSeconds: 30
          failureThreshold: 3
        
        env:
        - name: MODEL_NAME
          value: "prajjwal1/bert-tiny"
        - name: BATCH_SIZE
          value: "32"
        
        # 卷挂载：缓存模型
        volumeMounts:
        - name: model-cache
          mountPath: /root/.cache/huggingface
      
      # 卷定义：emptyDir 用于缓存
      volumes:
      - name: model-cache
        emptyDir:
          sizeLimit: 2Gi
      
      # 中止宽限期：留给应用优雅关闭
      terminationGracePeriodSeconds: 30
```

**关键特性**:
- 滚动更新策略：maxSurge=1, maxUnavailable=0（零停机部署）
- 初始化容器：预加载模型，加快启动
- 模型缓存卷：使用 emptyDir 存储预下载的模型
- 节点亲和性：可限制在特定节点（如 GPU）
- Pod 反亲和性：分散部署避免单点故障

---

#### 1.4 Service 配置

**文件**: `k8s/services.yaml`

```yaml
---
# Coordinator Service
apiVersion: v1
kind: Service
metadata:
  name: coordinator
  namespace: distai
  labels:
    app: coordinator
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
    protocol: TCP
    name: http
  selector:
    app: coordinator

---
# BERT Worker Service
apiVersion: v1
kind: Service
metadata:
  name: bert-worker
  namespace: distai
  labels:
    app: bert-worker
spec:
  type: ClusterIP
  clusterIP: None  # Headless Service，支持 DNS 负载均衡
  ports:
  - port: 9001
    targetPort: 9001
    protocol: TCP
  selector:
    app: bert-worker

---
# MobileNet Worker Service
apiVersion: v1
kind: Service
metadata:
  name: mobilenet-worker
  namespace: distai
  labels:
    app: mobilenet-worker
spec:
  type: ClusterIP
  clusterIP: None
  ports:
  - port: 9002
    targetPort: 9002
    protocol: TCP
  selector:
    app: mobilenet-worker

---
# CLIP Worker Service
apiVersion: v1
kind: Service
metadata:
  name: clip-worker
  namespace: distai
  labels:
    app: clip-worker
spec:
  type: ClusterIP
  clusterIP: None
  ports:
  - port: 9003
    targetPort: 9003
    protocol: TCP
  selector:
    app: clip-worker
```

**Service 类型选择**:
- Coordinator: `ClusterIP`（内部 API 网关）
- Workers: `ClusterIP` + `Headless`（DNS 负载均衡）

---

### Phase 2: 配置和可观测性（2.5小时）

#### 2.1 ConfigMap - 应用配置

**文件**: `k8s/configmap.yaml`

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: distai-config
  namespace: distai
data:
  # Coordinator 配置
  coordinator-config.yaml: |
    max_retries: 3
    retry_backoff: 0.5
    health_check_interval: 5
    request_timeout: 10
    log_level: INFO
  
  # 应用启动脚本
  startup.sh: |
    #!/bin/bash
    set -e
    echo "Starting DistAI Coordinator..."
    python3 coordinator.py
```

---

#### 2.2 Secrets - 敏感信息

**文件**: `k8s/secrets.yaml`

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: distai-secrets
  namespace: distai
type: Opaque
stringData:
  # 模型下载令牌（Hugging Face）
  huggingface-token: "your-token-here"
  
  # API 密钥（如果需要）
  api-key: "your-api-key-here"
```

**注意**: 实际部署时用 External Secrets 或 Sealed Secrets

---

#### 2.3 HPA - 自动水平扩展

**文件**: `k8s/hpa.yaml`

```yaml
---
# BERT Worker HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: bert-worker-hpa
  namespace: distai
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: bert-worker
  
  minReplicas: 2      # 最少 2 个副本
  maxReplicas: 10     # 最多 10 个副本
  
  metrics:
  # CPU 基准：当平均 CPU 超过 70% 时扩展
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  
  # 内存基准：当平均内存超过 80% 时扩展
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  
  # 自定义指标：请求队列深度（如果使用 Prometheus）
  - type: Pods
    pods:
      metric:
        name: http_requests_queued
      target:
        type: AverageValue
        averageValue: "50"
  
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 缩容前等待 5 分钟
      policies:
      - type: Percent
        value: 50                       # 一次最多减少 50%
        periodSeconds: 60
    
    scaleUp:
      stabilizationWindowSeconds: 0    # 立即扩容
      policies:
      - type: Percent
        value: 100                      # 一次最多增加 100%
        periodSeconds: 30

---
# MobileNet Worker HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mobilenet-worker-hpa
  namespace: distai
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mobilenet-worker
  
  minReplicas: 2
  maxReplicas: 8
  
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70

---
# CLIP Worker HPA
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: clip-worker-hpa
  namespace: distai
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: clip-worker
  
  minReplicas: 2
  maxReplicas: 8
  
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**HPA 工作原理**:
```
High Load
    ↓
CPU > 70% → Scale Up (double replicas)
    ↓
Low Load (5 min)
    ↓
CPU < 70% → Scale Down (half replicas)
```

---

### Phase 3: 网络和安全（2小时）

#### 3.1 Ingress - 外部访问

**文件**: `k8s/ingress.yaml`

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: distai-ingress
  namespace: distai
  annotations:
    # NGINX Ingress Controller
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/rate-limit: "100"  # 限流：100 req/s
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
    
    # Cert-Manager（自动 HTTPS）
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  # ingressClassName: nginx
  
  tls:
  - hosts:
    - distai.example.com
    secretName: distai-tls
  
  rules:
  - host: distai.example.com
    http:
      paths:
      - path: /infer
        pathType: Prefix
        backend:
          service:
            name: coordinator
            port:
              number: 8000
      
      - path: /status
        pathType: Prefix
        backend:
          service:
            name: coordinator
            port:
              number: 8000
      
      - path: /metrics
        pathType: Prefix
        backend:
          service:
            name: coordinator
            port:
              number: 8000
```

---

#### 3.2 NetworkPolicy - 网络安全

**文件**: `k8s/network-policy.yaml`

```yaml
---
# Deny all ingress 默认策略
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: distai
spec:
  podSelector: {}
  policyTypes:
  - Ingress

---
# 允许 Coordinator 接收来自 Ingress 的流量
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-coordinator-from-ingress
  namespace: distai
spec:
  podSelector:
    matchLabels:
      app: coordinator
  policyTypes:
  - Ingress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000

---
# 允许 Coordinator 到 Workers 的通信
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-coordinator-to-workers
  namespace: distai
spec:
  podSelector:
    matchLabels:
      app: bert-worker
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: coordinator
    ports:
    - protocol: TCP
      port: 9001
```

---

#### 3.3 RBAC - 权限控制

**文件**: `k8s/rbac.yaml`

```yaml
---
# ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: distai-app
  namespace: distai

---
# Role - 定义权限
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: distai-role
  namespace: distai
rules:
# 允许读取 ConfigMap 和 Secret
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]

# 允许读取 Pods（用于服务发现）
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]

# 允许读写持久卷（可选）
- apiGroups: [""]
  resources: ["persistentvolumeclaims"]
  verbs: ["get", "list"]

---
# RoleBinding - 绑定权限到 ServiceAccount
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: distai-rolebinding
  namespace: distai
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: distai-role
subjects:
- kind: ServiceAccount
  name: distai-app
  namespace: distai
```

---

### Phase 4: 监控和日志（可选但强烈推荐）

#### 4.1 PodMonitor - Prometheus 集成

**文件**: `k8s/pod-monitor.yaml`

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: distai-monitor
  namespace: distai
spec:
  selector:
    matchLabels:
      app: coordinator
  
  podMetricsEndpoints:
  - port: http
    path: /metrics
    interval: 30s
```

---

#### 4.1 StatefulSet 选项（如果需要持久化）

**文件**: `k8s/coordinator-statefulset.yaml`（可选）

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: coordinator
  namespace: distai
spec:
  serviceName: coordinator
  replicas: 3  # 高可用
  selector:
    matchLabels:
      app: coordinator
  
  template:
    metadata:
      labels:
        app: coordinator
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - coordinator
            topologyKey: kubernetes.io/hostname
      
      containers:
      - name: coordinator
        image: distai-coordinator:latest
        ports:
        - containerPort: 8000
          name: http
        
        volumeMounts:
        - name: data
          mountPath: /data
  
  # 持久卷
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 10Gi
```

---

## 📋 完整部署步骤

### 第一步：构建镜像

```bash
# 构建 Coordinator 镜像
docker build -t distai-coordinator:latest ./coordinator

# 构建 BERT Worker 镜像
docker build -t distai-bert-worker:latest ./workers -f ./workers/Dockerfile --build-arg WORKER_TYPE=bert

# 构建 MobileNet Worker 镜像
docker build -t distai-mobilenet-worker:latest ./workers -f ./workers/Dockerfile --build-arg WORKER_TYPE=mobilenet

# 构建 CLIP Worker 镜像
docker build -t distai-clip-worker:latest ./workers -f ./workers/Dockerfile --build-arg WORKER_TYPE=clip

# 推送到 Docker Registry（可选）
docker tag distai-coordinator:latest your-registry/distai-coordinator:latest
docker push your-registry/distai-coordinator:latest
```

### 第二步：部署到 K8s

```bash
# 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 部署 ConfigMap 和 Secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml

# 部署 RBAC
kubectl apply -f k8s/rbac.yaml

# 部署 Services
kubectl apply -f k8s/services.yaml

# 部署 Deployments
kubectl apply -f k8s/coordinator-deployment.yaml
kubectl apply -f k8s/bert-worker-deployment.yaml
kubectl apply -f k8s/mobilenet-worker-deployment.yaml
kubectl apply -f k8s/clip-worker-deployment.yaml

# 配置 HPA
kubectl apply -f k8s/hpa.yaml

# 部署 Ingress（如果有 Ingress Controller）
kubectl apply -f k8s/ingress.yaml

# 部署网络策略
kubectl apply -f k8s/network-policy.yaml

# 验证部署
kubectl get pods -n distai
kubectl get services -n distai
kubectl get deployments -n distai
```

### 第三步：验证和监控

```bash
# 查看 Pod 状态
kubectl get pods -n distai -w

# 查看日志
kubectl logs -n distai -l app=coordinator -f

# 端口转发（本地测试）
kubectl port-forward -n distai svc/coordinator 8000:8000

# 发送测试请求
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"text": "test"}'

# 查看 HPA 状态
kubectl get hpa -n distai

# 查看指标
kubectl top nodes
kubectl top pods -n distai

# 监控事件
kubectl get events -n distai --sort-by='.lastTimestamp'
```

---

## 🎯 快速参考：部署文件树

```
k8s/
├── namespace.yaml              # Namespace 定义
├── coordinator-deployment.yaml # Coordinator 部署
├── bert-worker-deployment.yaml # Worker 部署（可复制用于其他 Worker）
├── mobilenet-worker-deployment.yaml
├── clip-worker-deployment.yaml
├── services.yaml               # ClusterIP Services
├── configmap.yaml              # 配置文件
├── secrets.yaml                # 敏感信息
├── hpa.yaml                    # 自动扩展
├── rbac.yaml                   # 权限控制
├── network-policy.yaml         # 网络安全
├── ingress.yaml                # 外部访问
├── pod-monitor.yaml            # Prometheus 监控
└── kustomization.yaml          # Kustomize 配置（可选）
```

---

## 📊 对比：Docker Compose vs Kubernetes

| 方面 | Docker Compose | Kubernetes |
|------|---|---|
| **部署** | 简单（`docker-compose up`) | 复杂（需要多个 manifests） |
| **副本** | 固定数量 | 动态自动扩展 |
| **高可用** | 无（单点故障） | ✓ 内置（多副本+健康检查） |
| **更新** | 停机更新 | 零停机滚动更新 |
| **资源管理** | 手动 | 自动调度和限制 |
| **网络** | Docker network | Service + DNS + 负载均衡 |
| **存储** | emptyDir（临时） | PersistentVolume（持久） |
| **监控** | 基础（Docker stats） | 完整（Prometheus + Grafana） |
| **适用场景** | 开发/演示 | **生产环境** |

---

## 💡 简历价值提升

### 从 Docker Compose 到 K8s

```
项目说法 1（当前）：
"使用 Docker Compose 部署分布式 AI 推理系统"

↓ 升级后

项目说法 2（K8s）：
"使用 Kubernetes 部署生产级分布式 AI 推理系统，包括：
• 多副本 Deployment 与滚动更新（零停机）
• Pod Anti-affinity 避免单点故障
• HPA 自动扩展（CPU 基准：70%）
• ConfigMap + Secrets 配置管理
• NetworkPolicy 网络隔离
• RBAC 访问控制
• Readiness/Liveness/Startup 三层健康检查
• 支持 Prometheus 监控集成"
```

### 面试官视角的价值

| 角度 | Docker Compose | Kubernetes |
|------|---|---|
| **技术深度** | 基础容器化 | **生产级编排** |
| **可靠性** | 演示级 | **企业级** |
| **扩展性** | 静态部署 | **动态可扩展** |
| **竞争力** | 中等 | **大幅提升** |
| **招聘相关度** | DevOps 初级 | **DevOps/SRE 中级+** |

---

## ⏱️ 时间投入 vs 收益

| 投入 | 收益 | 性价比 |
|------|------|--------|
| 9-11 小时 | 职业竞争力大幅提升 | ⭐⭐⭐⭐⭐ |
| | 展示生产环保部署能力 | |
| | 大公司必备技能 | |
| | 简历直接加分 | |

---

## 🚀 立即开始

### 最小化 K8s 部署（1小时快速版）

如果时间紧张，最低限度这样做：

```yaml
# k8s/quick-deploy.yaml（All-in-one）
apiVersion: v1
kind: Namespace
metadata:
  name: distai

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coordinator
  namespace: distai
spec:
  replicas: 1
  selector:
    matchLabels:
      app: coordinator
  template:
    metadata:
      labels:
        app: coordinator
    spec:
      containers:
      - name: coordinator
        image: distai-coordinator:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 20

---
apiVersion: v1
kind: Service
metadata:
  name: coordinator
  namespace: distai
spec:
  type: ClusterIP
  ports:
  - port: 8000
  selector:
    app: coordinator
```

部署只需：
```bash
kubectl apply -f k8s/quick-deploy.yaml
kubectl port-forward -n distai svc/coordinator 8000:8000
```

---

## 📚 推荐资源

1. **K8s 官方文档**: https://kubernetes.io/docs/
2. **Deployment 最佳实践**: https://kubernetes.io/docs/concepts/workloads/controllers/deployment/
3. **HPA 完整指南**: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
4. **网络策略**: https://kubernetes.io/docs/concepts/services-networking/network-policies/

---

## 🎯 下一步建议

1. **立即行动**（1小时）
   - 创建基础 Namespace 和 Deployment manifests
   - 在本地 minikube 测试

2. **中期完善**（3-5小时）
   - 添加 HPA、Ingress、RBAC
   - 集成 Prometheus 监控
   - 编写部署文档

3. **高级优化**（可选）
   - 使用 Helm Chart 模板化
   - 集成 GitOps（ArgoCD）
   - 多集群部署
   - Service Mesh（Istio）

---

**建议：现在就开始写 K8s manifests！** 🚀
