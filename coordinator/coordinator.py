"""
Coordinator Service for Distributed AI Inference System

Responsibilities:
- Route inference requests to appropriate workers based on input modality
- Monitor worker health and availability
- Track performance metrics and maintain request logs
- Implement fault tolerance with retry logic and exponential backoff

Request Routing Logic:
- Text only → BERT Worker (text embeddings)
- Image only → MobileNet Worker (image classification)
- Both → CLIP Worker (vision-language model)
"""

import time
import threading
import random
import requests
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Tuple
from flask import Flask, request, jsonify
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# ============================================================================
# Configuration
# ============================================================================

MAX_RETRIES = 3
RETRY_BACKOFF = 0.5  # seconds, multiplied by 2^attempt
HEALTH_CHECK_INTERVAL = 5  # seconds
REQUEST_TIMEOUT = 10  # seconds
MAX_LOG_SIZE = 50  # keep last N requests

# ============================================================================
# Logging Configuration
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Enums and Constants
# ============================================================================

class WorkerStatus(Enum):
    """Worker health status enumeration"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"

class WorkerType(Enum):
    """Task type to worker mapping"""
    BERT = "bert"
    MOBILENET = "mobilenet"
    CLIP = "clip"

# ============================================================================
# Prometheus Metrics
# ============================================================================

# Request counters
requests_total = Counter(
    'coordinator_requests_total',
    'Total inference requests processed',
    ['worker_type', 'status']
)

requests_retried = Counter(
    'coordinator_requests_retried_total',
    'Total requests that required retries',
    ['worker_type']
)

# Request latency histogram
request_latency_seconds = Histogram(
    'coordinator_request_latency_seconds',
    'Request latency in seconds',
    ['worker_type'],
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0)
)

# Worker status gauge
worker_status = Gauge(
    'coordinator_worker_status',
    'Worker status (1=online, 0=offline)',
    ['worker_id', 'worker_type']
)

# Active requests gauge
active_requests = Gauge(
    'coordinator_active_requests',
    'Number of active inference requests'
)

# ============================================================================
# Flask Application Initialization
# ============================================================================

app = Flask(__name__)

# Worker registry - defines available worker services
workers = {
    WorkerType.BERT.value: {
        "id": "worker1",
        "url": "http://worker1:9001",
        "status": WorkerStatus.OFFLINE.value,
        "type": WorkerType.BERT.value
    },
    WorkerType.MOBILENET.value: {
        "id": "worker2",
        "url": "http://worker2:9002",
        "status": WorkerStatus.OFFLINE.value,
        "type": WorkerType.MOBILENET.value
    },
    WorkerType.CLIP.value: {
        "id": "worker3",
        "url": "http://worker3:9003",
        "status": WorkerStatus.OFFLINE.value,
        "type": WorkerType.CLIP.value
    },
}

# Request log for observability
request_log = []

# ============================================================================
# Health Check and Monitoring
# ============================================================================

def health_check():
    """
    Periodically check health of all workers.
    Updates worker status based on connectivity and response time.
    """
    while True:
        for worker_type, worker_info in workers.items():
            try:
                start = time.time()
                response = requests.get(
                    f"{worker_info['url']}/status",
                    timeout=2
                )
                latency = time.time() - start

                if response.status_code == 200:
                    worker_info["status"] = WorkerStatus.ONLINE.value
                    worker_info["last_check"] = datetime.utcnow().isoformat()
                    worker_status.labels(
                        worker_id=worker_info["id"],
                        worker_type=worker_type
                    ).set(1)
                    logger.debug(f"Worker {worker_info['id']} is online (latency: {latency*1000:.1f}ms)")
                else:
                    worker_info["status"] = WorkerStatus.OFFLINE.value
                    worker_status.labels(
                        worker_id=worker_info["id"],
                        worker_type=worker_type
                    ).set(0)
                    logger.warning(f"Worker {worker_info['id']} returned status {response.status_code}")

            except requests.exceptions.Timeout:
                worker_info["status"] = WorkerStatus.OFFLINE.value
                worker_status.labels(
                    worker_id=worker_info["id"],
                    worker_type=worker_type
                ).set(0)
                logger.warning(f"Worker {worker_info['id']} health check timeout")

            except Exception as e:
                worker_info["status"] = WorkerStatus.OFFLINE.value
                worker_status.labels(
                    worker_id=worker_info["id"],
                    worker_type=worker_type
                ).set(0)
                logger.error(f"Health check error for {worker_info['id']}: {str(e)}")

        time.sleep(HEALTH_CHECK_INTERVAL)

# ============================================================================
# Request Input Validation and Routing
# ============================================================================

def validate_and_route(data: Dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate input data and determine target worker type.

    Args:
        data: JSON request body

    Returns:
        Tuple of (worker_type, error_message)
        - worker_type: One of 'bert', 'mobilenet', 'clip' if valid
        - error_message: Error description if invalid, None otherwise
    """
    has_text = (
        "text" in data
        and isinstance(data["text"], str)
        and data["text"].strip()
    )
    has_image = (
        "image_base64" in data
        and isinstance(data["image_base64"], str)
        and data["image_base64"].strip()
    )

    if not (has_text or has_image):
        return None, "Invalid input: must provide either 'text', 'image_base64', or both"

    # Route to appropriate worker based on input modality
    if has_text and not has_image:
        return WorkerType.BERT.value, None
    elif has_image and not has_text:
        return WorkerType.MOBILENET.value, None
    else:  # both text and image
        return WorkerType.CLIP.value, None

# ============================================================================
# Main Inference Endpoint
# ============================================================================

@app.route("/infer", methods=["POST"])
def infer():
    """
    Handle inference requests with intelligent routing and retry logic.

    Request body (JSON):
    {
        "text": "optional text input",
        "image_base64": "optional base64 encoded image"
    }

    Response (JSON):
    {
        "result": <model output>,
        "worker_id": "worker_x",
        "latency_ms": <milliseconds>,
        "request_id": <random id>,
        "timestamp": "ISO 8601 timestamp"
    }

    Error responses:
    - 400: Invalid input
    - 503: Worker unavailable or unhealthy
    - 504: All retry attempts exhausted
    """
    request_id = random.randint(100000, 999999)
    active_requests.inc()

    try:
        data = request.json or {}

        # Validate and route
        worker_type, error_msg = validate_and_route(data)
        if error_msg:
            logger.warning(f"[{request_id}] Invalid input: {error_msg}")
            return jsonify({
                "error": error_msg,
                "request_id": request_id
            }), 400

        worker_info = workers[worker_type]

        # Check if worker is available
        if worker_info["status"] != WorkerStatus.ONLINE.value:
            logger.error(f"[{request_id}] Target worker {worker_info['id']} is {worker_info['status']}")
            requests_total.labels(worker_type=worker_type, status="worker_unavailable").inc()
            return jsonify({
                "error": f"Worker {worker_info['id']} is currently {worker_info['status']}",
                "worker_id": worker_info["id"],
                "request_id": request_id
            }), 503

        logger.info(f"[{request_id}] Routing {worker_type} request to {worker_info['id']}")

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                start_time = time.time()
                response = requests.post(
                    f"{worker_info['url']}/infer",
                    json=data,
                    timeout=REQUEST_TIMEOUT
                )
                latency_ms = (time.time() - start_time) * 1000

                if response.status_code != 200:
                    logger.warning(f"[{request_id}] Worker returned status {response.status_code}")
                    last_error = f"Worker HTTP {response.status_code}"
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_BACKOFF * (2 ** attempt)
                        time.sleep(wait_time)
                    continue

                # Success
                result = response.json()
                request_log.append({
                    "request_id": request_id,
                    "worker_id": worker_info["id"],
                    "worker_type": worker_type,
                    "latency_ms": latency_ms,
                    "attempts": attempt + 1,
                    "status": "success",
                    "timestamp": datetime.utcnow().isoformat()
                })

                requests_total.labels(worker_type=worker_type, status="success").inc()
                request_latency_seconds.labels(worker_type=worker_type).observe(latency_ms / 1000)
                if attempt > 0:
                    requests_retried.labels(worker_type=worker_type).inc()

                logger.info(f"[{request_id}] Success after {attempt + 1} attempt(s), latency: {latency_ms:.1f}ms")

                # Keep log size bounded
                if len(request_log) > MAX_LOG_SIZE:
                    request_log.pop(0)

                return jsonify({
                    "result": result,
                    "worker_id": worker_info["id"],
                    "latency_ms": latency_ms,
                    "request_id": request_id,
                    "attempts": attempt + 1,
                    "timestamp": datetime.utcnow().isoformat()
                }), 200

            except requests.exceptions.Timeout:
                last_error = f"Timeout after {REQUEST_TIMEOUT}s"
                logger.warning(f"[{request_id}] Attempt {attempt + 1}: {last_error}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF * (2 ** attempt)
                    logger.info(f"[{request_id}] Retrying in {wait_time:.1f}s (exponential backoff)")
                    time.sleep(wait_time)

            except requests.exceptions.RequestException as e:
                last_error = str(e)
                logger.warning(f"[{request_id}] Attempt {attempt + 1}: {last_error}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_BACKOFF * (2 ** attempt)
                    logger.info(f"[{request_id}] Retrying in {wait_time:.1f}s (exponential backoff)")
                    time.sleep(wait_time)

        # All retries exhausted
        request_log.append({
            "request_id": request_id,
            "worker_id": worker_info["id"],
            "worker_type": worker_type,
            "attempts": MAX_RETRIES,
            "status": "failed",
            "error": last_error,
            "timestamp": datetime.utcnow().isoformat()
        })

        requests_total.labels(worker_type=worker_type, status="failed").inc()
        logger.error(f"[{request_id}] Failed after {MAX_RETRIES} attempts: {last_error}")

        if len(request_log) > MAX_LOG_SIZE:
            request_log.pop(0)

        return jsonify({
            "error": f"Worker request failed after {MAX_RETRIES} retries: {last_error}",
            "worker_id": worker_info["id"],
            "request_id": request_id,
            "attempts": MAX_RETRIES
        }), 504

    finally:
        active_requests.dec()

# ============================================================================
# Health and Status Endpoints
# ============================================================================

@app.route("/status")
def status():
    """
    Get system status including coordinator health, worker status, and recent request logs.

    Returns:
    {
        "coordinator": "online",
        "timestamp": "ISO 8601 timestamp",
        "workers": {
            "bert": {"id": "worker1", "status": "online", ...},
            ...
        },
        "recent_requests": [...],
        "stats": {"total_requests": N, "success_rate": 0.95, ...}
    }
    """
    total_requests = len(request_log)
    successful_requests = sum(1 for r in request_log if r["status"] == "success")
    success_rate = (
        successful_requests / total_requests if total_requests > 0 else 0
    )

    avg_latency = 0
    if successful_requests > 0:
        avg_latency = sum(
            r["latency_ms"] for r in request_log if r["status"] == "success"
        ) / successful_requests

    return jsonify({
        "coordinator": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "workers": workers,
        "recent_requests": request_log[-10:],
        "stats": {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": total_requests - successful_requests,
            "success_rate": success_rate,
            "avg_latency_ms": avg_latency
        }
    }), 200

@app.route("/metrics")
def metrics():
    """
    Prometheus metrics endpoint for monitoring system performance.
    Exposes counters, histograms, and gauges for external monitoring systems.
    """
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route("/health")
def health():
    """Simple health check endpoint for load balancers"""
    return jsonify({"status": "ok"}), 200

# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

# ============================================================================
# Application Startup
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting Coordinator Service...")
    logger.info(f"Configuration: MAX_RETRIES={MAX_RETRIES}, RETRY_BACKOFF={RETRY_BACKOFF}s, HEALTH_CHECK_INTERVAL={HEALTH_CHECK_INTERVAL}s")

    # Start health check thread
    health_check_thread = threading.Thread(target=health_check, daemon=True)
    health_check_thread.start()
    logger.info("Health check thread started")

    # Start Flask application
    app.run(host="0.0.0.0", port=8000, debug=False)
