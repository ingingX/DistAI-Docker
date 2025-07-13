# DistAI-Docker

implementation using Docker.
My first Docker application.

## 项目结构

```
ai-inference-project/
├── coordinator/
│   ├── Dockerfile
│   ├── coordinator.py
│   └── requirements.txt
├── workers/
│   ├── Dockerfile
│   ├── w1-BERT.py
│   ├── w2-MobileNet.py
│   ├── w3-CLIP.py
│   ├── worker_test.py
│   └── requirements.txt
├── testerClient/
│   ├── Dockerfile
│   ├── tester.py
│   └── requirements.txt
├── docker-compose.yml
├── .dockerignore
├── Makefile
└── README.md
```

## 服务架构

- **协调器 (Coordinator)**: 端口8000，负责请求分发和负载均衡
- **BERT工作节点**: 端口9001，提供文本嵌入服务
- **MobileNet工作节点**: 端口9002，提供图像分类服务
- **CLIP工作节点**: 端口9003，提供多模态嵌入服务
- **测试客户端**: 用于测试系统功能

## 快速开始

### 1. 环境准备

确保安装了以下软件：
- Docker (20.10+)
- Docker Compose (2.0+)
- Make (可选，用于简化命令)

### 2. 构建和启动

```bash
# 使用 Make (推荐)
make build    # 构建所有镜像
make up       # 启动所有服务
make logs     # 查看日志

# 或使用 Docker Compose
docker-compose build
docker-compose up -d
docker-compose logs -f
```

### 3. 健康检查

```bash
# 检查服务状态
make health

# 或直接访问
curl http://localhost:8000/health
```

### 4. 运行测试

```bash
# 运行测试客户端
make test

# 或
docker-compose --profile testing up --build tester
```

## 使用说明

### 发送推理请求

```bash
# 文本推理 (BERT/CLIP)
curl -X POST "http://localhost:8000/infer" \
     -H "Content-Type: application/json" \
     -d '{"input": "Hello world"}'

# 图像推理 (MobileNet)
curl -X POST "http://localhost:9002/infer" \
     -H "Content-Type: application/json" \
     -d '{"image_base64": "base64_encoded_image_data"}'
```

### 查看工作节点状态

```bash
curl http://localhost:8000/workers
```

## 配置选项

### 环境变量

每个工作节点支持以下环境变量：

- `MODEL`: 模型名称 (BERT/CLIP)
- `WORKER_ID`: 工作节点ID
- `FAIL_RATE`: 模拟失败率 (0.0-1.0)
- `PORT`: 服务端口
- `PYTHONUNBUFFERED`: Python输出缓冲

### 扩展工作节点

```bash
# 扩展到3个实例
make scale-workers WORKERS=3

# 或
docker-compose up -d --scale worker-bert=3 --scale worker-mobilenet=3 --scale worker-clip=3
```

## 常用命令

### Make 命令

```bash
make help          # 显示帮助
make build         # 构建镜像
make up            # 启动服务
make down          # 停止服务
make restart       # 重启服务
make logs          # 查看所有日志
make logs-coordinator  # 查看协调器日志
make logs-workers  # 查看工作节点日志
make clean         # 清理容器和镜像
make test          # 运行测试
make health        # 检查健康状态
make dev           # 开发模式 (带日志)
make prod          # 生产模式 (后台运行)
```

### Docker Compose 命令

```bash
docker-compose build           # 构建镜像
docker-compose up -d          # 后台启动
docker-compose down           # 停止服务
docker-compose logs -f        # 查看日志
docker-compose ps             # 查看服务状态
docker-compose exec coordinator bash  # 进入协调器容器
```

## 监控和故障排除

### 检查服务状态

```bash
# 查看所有服务状态
docker-compose ps

# 查看特定服务日志
docker-compose logs worker-bert
```

### 常见问题

1. **端口冲突**: 确保8000-9003端口未被占用
2. **内存不足**: AI模型需要足够的内存，建议至少4GB
3. **网络问题**: 确保容器间网络连通性
4. **模型下载**: 首次启动会下载模型，可能需要较长时间

### 性能优化

1. **缓存卷**: 使用持久化卷缓存模型文件
2. **资源限制**: 在docker-compose.yml中设置资源限制
3. **并发处理**: 通过扩展工作节点提高并发能力

## 生产部署建议

1. **安全性**:
   - 使用非root用户运行容器
   - 配置防火墙规则
   - 使用secrets管理敏感信息

2. **高可用性**:
   - 部署多个工作节点实例
   - 使用负载均衡器
   - 配置健康检查和自动重启

3. **监控**:
   - 集成Prometheus/Grafana
   - 设置日志聚合
   - 配置告警系统

4. **存储**:
   - 使用外部存储卷
   - 配置模型缓存策略
   - 定期备份数据

## 开发说明

### 添加新的工作节点

1. 在`workers/`目录创建新的Python文件
2. 实现FastAPI应用和`/infer`、`/health`端点
3. 添加到docker-compose.yml中
4. 更新coordinator.py中的WORKERS列表

### 自定义模型

修改环境变量`MODEL`来使用不同的预训练模型：

```yaml
environment:
  - MODEL=bert-base-uncased  # 使用不同的BERT模型
```

## 许可证

MIT License