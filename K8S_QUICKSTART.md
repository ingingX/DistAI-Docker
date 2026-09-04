# Kubernetes 快速开始指南

## ⚡ 5分钟快速开始

### 前提条件
```bash
# 检查是否安装了 kubectl
kubectl version

# 本地开发：安装 minikube
brew install minikube  # macOS
# 或从 https://minikube.sigs.k8s.io/docs/start/ 下载

# 启动 minikube
minikube start --cpus=4 --memory=8192
```

### 一键部署（所有组件）

```bash
# 切换到项目目录
cd /home/elyjah/Documents/GitHub/DistAI-Docker

# 创建 Docker 镜像（需要本地构建）
docker build -t distai-coordinator:latest ./coordinator
docker build -t distai-bert-worker:latest ./workers --build-arg WORKER_TYPE=bert
docker build -t distai-mobilenet-worker:latest ./workers --build-arg WORKER_TYPE=mobilenet
docker build -t distai-clip-worker:latest ./workers --build-arg WORKER_TYPE=clip

# 如果用 minikube，加载镜像到 minikube
minikube image load distai-coordinator:latest
minikube image load distai-bert-worker:latest
minikube image load distai-mobilenet-worker:latest
minikube image load distai-clip-worker:latest

# 一键部署所有 K8s 资源
kubectl apply -f k8s/distai-all-in-one.yaml

# 等待 Pod 启动
kubectl get pods -n distai -w

# 查看部署状态
kubectl get deployments -n distai
kubectl get services -n distai
kubectl get hpa -n distai

# 端口转发（本地测试）
kubectl port-forward -n distai svc/coordinator 8000:8000

# 在另一个终端发送测试请求
curl -X POST http://localhost:8000/infer \
  -H "Content-Type: application/json" \
  -d '{"text": "hello world"}'
```

---

## 📋 常用命令速查表

### 查看资源状态

```bash
# 查看所有 Pod
kubectl get pods -n distai

# 查看具体 Pod 详情
kubectl describe pod <pod-name> -n distai

# 查看 Pod 日志
kubectl logs <pod-name> -n distai

# 实时查看日志
kubectl logs <pod-name> -n distai -f

# 查看最后 100 行日志
kubectl logs <pod-name> -n distai --tail=100

# 查看所有资源
kubectl get all -n distai
```

### 管理部署

```bash
# 查看 Deployment
kubectl get deployments -n distai

# 查看 Deployment 详情
kubectl describe deployment coordinator -n distai

# 查看副本数
kubectl get replicasets -n distai

# 手动扩展副本数
kubectl scale deployment bert-worker --replicas=5 -n distai

# 查看扩展历史
kubectl rollout history deployment coordinator -n distai

# 回滚到上一个版本
kubectl rollout undo deployment coordinator -n distai

# 回滚到指定版本
kubectl rollout undo deployment coordinator --to-revision=1 -n distai
```

### 监控和调试

```bash
# 查看 Pod 资源使用
kubectl top pods -n distai

# 查看 Node 资源使用
kubectl top nodes

# 查看事件（按时间排序）
kubectl get events -n distai --sort-by='.lastTimestamp'

# 进入 Pod 容器
kubectl exec -it <pod-name> -n distai /bin/bash

# 执行单条命令
kubectl exec <pod-name> -n distai -- curl http://localhost:8000/status

# 查看 HPA 状态
kubectl get hpa -n distai

# 查看 HPA 详细信息
kubectl describe hpa bert-worker-hpa -n distai
```

### 网络和服务

```bash
# 查看 Service
kubectl get services -n distai

# 端口转发（访问 Pod）
kubectl port-forward -n distai pod/<pod-name> 8000:8000

# 端口转发（访问 Service）
kubectl port-forward -n distai svc/coordinator 8000:8000

# 查看 Service 端点
kubectl get endpoints -n distai

# DNS 查询（Pod 内部）
kubectl exec -it <pod-name> -n distai -- nslookup coordinator.distai.svc.cluster.local
```

### 更新和部署

```bash
# 检查更新状态
kubectl rollout status deployment coordinator -n distai

# 查看当前 Pod 用的镜像
kubectl get pods -n distai -o jsonpath='{.items[*].spec.containers[*].image}'

# 更新镜像（触发滚动更新）
kubectl set image deployment/coordinator \
  coordinator=distai-coordinator:v2 \
  -n distai

# 暂停更新
kubectl rollout pause deployment coordinator -n distai

# 恢复更新
kubectl rollout resume deployment coordinator -n distai
```

### 配置管理

```bash
# 查看 ConfigMap
kubectl get configmap -n distai

# 查看 ConfigMap 内容
kubectl describe configmap distai-config -n distai

# 编辑 ConfigMap
kubectl edit configmap distai-config -n distai

# 查看 Secret
kubectl get secret -n distai

# 创建 Secret
kubectl create secret generic distai-secrets \
  --from-literal=token=mytoken \
  -n distai
```

### 清理和删除

```bash
# 删除单个 Pod
kubectl delete pod <pod-name> -n distai

# 删除 Deployment（自动删除 Pod）
kubectl delete deployment coordinator -n distai

# 删除所有资源
kubectl delete all -n distai

# 删除整个命名空间（包括所有资源）
kubectl delete namespace distai

# 删除使用特定标签的所有资源
kubectl delete pods -l app=coordinator -n distai
```

---

## 🔍 故障排查

### Pod 无法启动

```bash
# 检查 Pod 状态
kubectl describe pod <pod-name> -n distai

# 常见原因：
# 1. 镜像不存在：ImagePullBackOff
kubectl set image deployment/coordinator \
  coordinator=distai-coordinator:latest \
  -n distai

# 2. 资源不足：Pending
kubectl describe node
kubectl top nodes

# 3. 健康检查失败：CrashLoopBackOff
kubectl logs <pod-name> -n distai
```

### 无法连接到 Pod

```bash
# 查看 Service 端点
kubectl get endpoints coordinator -n distai

# 测试 Pod 间通信
kubectl exec -it <pod-name> -n distai -- \
  curl http://coordinator.distai.svc.cluster.local:8000/health

# 查看网络策略
kubectl get networkpolicies -n distai

# 删除网络策略临时测试
kubectl delete networkpolicies -n distai
```

### HPA 无法扩展

```bash
# 查看 HPA 状态
kubectl describe hpa bert-worker-hpa -n distai

# 查看 metrics server（需要部署）
kubectl get deployment metrics-server -n kube-system

# 查看 Pod 指标
kubectl get --raw /apis/metrics.k8s.io/v1beta1/namespaces/distai/pods
```

### 日志问题

```bash
# 查看前 50 行日志
kubectl logs <pod-name> -n distai --head=50

# 查看从时间戳以来的日志
kubectl logs <pod-name> -n distai --since=1h

# 查看多个 Pod 的日志
kubectl logs -l app=coordinator -n distai

# 查看先前容器的日志（容器崩溃时）
kubectl logs <pod-name> -n distai --previous
```

---

## 📊 性能监控

### 查看资源指标

```bash
# 实时 Pod 资源使用
kubectl top pods -n distai

# Node 资源使用
kubectl top nodes

# 持续监控（更新间隔 2 秒）
watch 'kubectl top pods -n distai'
```

### 访问 Prometheus 指标

```bash
# 端口转发 Coordinator
kubectl port-forward -n distai svc/coordinator 8000:8000

# 查看 Prometheus 指标
curl http://localhost:8000/metrics

# 过滤特定指标
curl http://localhost:8000/metrics | grep coordinator_requests
```

---

## 🚀 高级用法

### 使用 kustomize 管理多环境

```bash
# 创建 kustomization.yaml
cat > k8s/kustomization.yaml << EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

bases:
- distai-all-in-one.yaml

patchesStrategicMerge:
- deployment-patch.yaml

configMapGenerator:
- name: distai-config
  env: config.env
EOF

# 应用
kubectl apply -k k8s/
```

### 使用 Helm（可选）

```bash
# 创建 Helm Chart
helm create distai

# 安装
helm install distai-release ./distai -n distai

# 升级
helm upgrade distai-release ./distai -n distai

# 回滚
helm rollback distai-release 1 -n distai
```

### GitOps 部署（ArgoCD）

```bash
# 安装 ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 创建 ArgoCD Application
kubectl apply -f - << EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: distai
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/ingingX/DistAI-Docker
    targetRevision: main
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: distai
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF
```

---

## 📚 参考资源

| 资源 | 链接 |
|------|------|
| K8s 官方文档 | https://kubernetes.io/docs/ |
| kubectl 速查表 | https://kubernetes.io/docs/reference/kubectl/cheatsheet/ |
| Deployment 最佳实践 | https://kubernetes.io/docs/concepts/workloads/controllers/deployment/ |
| HPA 文档 | https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/ |
| 网络策略 | https://kubernetes.io/docs/concepts/services-networking/network-policies/ |
| minikube 文档 | https://minikube.sigs.k8s.io/ |

---

## ✅ 检查清单

部署前检查：

- [ ] Docker 镜像已构建
- [ ] kubectl 已安装
- [ ] K8s 集群可访问
- [ ] 命名空间已创建

部署后检查：

- [ ] 所有 Pod 都是 Running 状态
- [ ] 所有 Service 有对应的端点
- [ ] 健康检查通过
- [ ] HPA 正常工作
- [ ] 可以访问 /metrics 端点

---

**现在就尝试部署吧！** 🚀
