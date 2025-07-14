#!/usr/bin/env python
"""
Batch Test Script

Sends 21 inference tasks in sequence:
- 7 text-only requests (BERT)
- 7 image-only requests (MobileNet)
- 7 image + text requests (CLIP)
Each response includes running time and model type.
Retries each request up to 3 if it fails.

--------
How to run:
docker-compose exec coordinator python /scripts/test_batch.py
--------

"""

import base64, requests, time, random

# from online test images
IMAGE_URLS = [
    "https://picsum.photos/seed/{}/256".format(i) for i in range(1, 11)
]

# Coordinator API endpoint
# Default on coordinator service URL, can be overridden by environment variable `--api http://localhost:8000/infer`
COORDINATOR_API = "http://coordinator:8000/infer"

# Download image and convert to base64
def fetch_image_b64(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return base64.b64encode(resp.content).decode()
    except Exception as e:
        print(f"[ERROR] Failed to fetch image from {url}: {e}")
        return ""

# Send request to coordinator
def send_request(payload: dict, index: int, task_type: str, max_retries: int = 3):
    attempt = 0
    while attempt < max_retries: 
        try:
            start = time.time()
            r = requests.post(COORDINATOR_API, json=payload, timeout=20)
            duration = time.time() - start
            # print result, sunning time, and model type
            print(f"[{index:02d}] {task_type.upper():9s} | Time: {duration:.2f}s | Attempt: {attempt+1} | Status: {r.status_code} | Result: {r.json()}")
            return
        except Exception as e:
            attempt += 1
            print(f"[{index:02d}] {task_type.upper():9s} | Attempt: {attempt} failed: {e}")
            time.sleep(0.5)
    print(f"[{index:02d}] {task_type.upper():9s} | All {max_retries} attempts failed.")

# main
def main():
    print("Starting batch test of 21 tasks...\n")
    for i in range(7):
        # Text-only (BERT)
        payload = {"text": f"This is test sentence number {i+1}."}
        send_request(payload, i+1, "bert")
        time.sleep(0.2)

    for i in range(7):
        # Image-only (MobileNet)
        img_b64 = fetch_image_b64(IMAGE_URLS[i % len(IMAGE_URLS)])
        if img_b64:
            payload = {"image_base64": img_b64}
            send_request(payload, i+8, "mobilenet")
        time.sleep(0.2)

    for i in range(7):
        # Both (CLIP)
        img_b64 = fetch_image_b64(IMAGE_URLS[(i + 3) % len(IMAGE_URLS)])
        if img_b64:
            payload = {
                "image_base64": img_b64,
                "text": f"A scenic image {i+1}"
            }
            send_request(payload, i+15, "clip")
        time.sleep(0.2)

    print("\n Batch test completed.")

if __name__ == "__main__":
    main()
