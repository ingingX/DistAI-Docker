"""
Coordinator service for routing inference requests to appropriate workers.

Routing logic:
- If request contains only text: send to BERT worker
- If request contains only image_base64: send to MobileNet worker
- If request contains both: send to CLIP worker

Performs periodic health checks to determine online/offline status of workers.
Logs request metadata and provides a simple status API.
"""

import time
import threading
import random
import requests
from flask import Flask, request, jsonify 
# Flask instead of FastAPI for simplicity, but no AsyncIO.
# Migration to FastAPI would be straightforward if needed.

# init Flask app and worker registry
app = Flask(__name__)

# worker registry as dict to assign workers to different types of tasks
workers = {
    "bert": {"id": "worker1", "url": "http://worker1:9001", "status": "unknown"},
    "mobilenet": {"id": "worker2", "url": "http://worker2:9002", "status": "unknown"},
    "clip": {"id": "worker3", "url": "http://worker3:9003", "status": "unknown"},
}

# init log
log = []

# define health check thread to check worker status
def health_check():
    while True:
        for w in workers.values():
            try:
                r = requests.get(w["url"] + "/status", timeout=1)
                w["status"] = "online" if r.status_code == 200 else "offline"
            except:
                w["status"] = "offline"
        time.sleep(5)

# POST task requests to workers
@app.route("/infer", methods=["POST"])
def infer():
    data = request.json or {}
    has_text = "text" in data and isinstance(data["text"], str) and data["text"].strip() != ""
    has_image = "image_base64" in data and isinstance(data["image_base64"], str) and data["image_base64"].strip() != ""

    # diff task types to diff workers 
    if has_text and not has_image:
        key = "bert"
    elif has_image and not has_text:
        key = "mobilenet"
    elif has_text and has_image:
        key = "clip"
    else:
        return jsonify({"error": "Invalid input: must provide either text, image_base64, or both"}), 400

    worker = workers[key]

    # randon request ID
    request_id = random.randint(1000, 9999)

    # attempts counter
    attempts = 0

    # retry for worker calls
    if worker["status"] != "online":
        return jsonify({"error": f"Target worker ({worker['id']}) is offline"}), 503
    try:
        start = time.time()
        r = requests.post(worker["url"] + "/infer", json=data, timeout=10)
        latency = time.time() - start
        log.append({
            "request_id": request_id,
            "worker_id": worker["id"],
            "latency": latency,
            "retries": attempts,
            "type": key
        })
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": f"Worker call failed: {str(e)}"}), 500

# status check
@app.route("/status")
def status():
    return jsonify({
        "coordinator": "online",
        "workers": workers,
        "logs": log[-10:]
    })

# main
if __name__ == "__main__":
    threading.Thread(target=health_check, daemon=True).start()
    # Start Flask app on localhost:8000 for coordinator
    app.run(host="0.0.0.0", port=8000) 