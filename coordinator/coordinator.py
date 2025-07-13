import asyncio
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import uvicorn

app = FastAPI()

# Define worker URLs
# These workers are expected to be running on localhost with different ports
WORKERS = [
    {"id": "w-BERT", "url": "http://localhost:9001"},
    {"id": "w-MobileNet", "url": "http://localhost:9002"},
    {"id": "w-CLIP", "url": "http://localhost:9003"}
]

worker_index = 0
lock = asyncio.Lock()

# Define the request base model for inference
class InferenceRequest(BaseModel):
    input: str

# Call FastAPI to POST inquiry to workers
@app.post("/infer")
async def infer(request: InferenceRequest):
    global worker_index
    retries = 3 # maximum number of retries if a worker fails

    for attempt in range(retries):
        async with lock:
            worker = WORKERS[worker_index % len(WORKERS)]
            worker_index += 1

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(f"{worker['url']}/infer", json={"input": request.input})
                response.raise_for_status()
                result = response.json()
                result["attempt"] = attempt + 1
                return result
        except Exception as e:
            print(f"Worker {worker['id']} failed on attempt {attempt+1}: {e}")
            continue

    raise HTTPException(status_code=500, detail="All workers failed after retries.")

# Get list of workers
@app.get("/workers")
async def get_workers():
    return WORKERS

# workders health check
@app.get("/health")
async def health_check():
    results = []
    async with httpx.AsyncClient(timeout=2.0) as client:
        for worker in WORKERS:
            try:
                r = await client.get(f"{worker['url']}/health")
                status = "online" if r.status_code == 200 else "unhealthy"
            except Exception:
                status = "offline"
            results.append({
                "id": worker["id"],
                "url": worker["url"],
                "status": status
            })
    return {
        "coordinator": "online",
        "workers": results
    }

if __name__ == "__main__":
    uvicorn.run("coordinator:app", host="0.0.0.0", port=8000)
