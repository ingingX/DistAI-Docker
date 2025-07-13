import random
import asyncio
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import torch
from transformers import BertTokenizer, BertModel

# Init model and environment variables
MODEL_NAME = os.getenv("MODEL", "prajjwal1/bert-tiny")
WORKER_ID = os.getenv("WORKER_ID", "w1-bert")
FAIL_RATE = float(os.getenv("FAIL_RATE", "0.2"))
DELAY_RANGE = (0.1, 1.0)  # Simulated delay range in seconds

print(f"[{WORKER_ID}] Loading model {MODEL_NAME}...")
tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)
model = BertModel.from_pretrained(MODEL_NAME)
model.eval()
print(f"[{WORKER_ID}] Model loaded.")

app = FastAPI()

class InferenceRequest(BaseModel):
    input: str

@app.post("/infer")
async def infer(request: InferenceRequest):
    # Simulate Network delay
    await asyncio.sleep(random.uniform(*DELAY_RANGE))

    # Simulate random Failure
    if random.random() < FAIL_RATE:
        raise HTTPException(status_code=500, detail=f"{WORKER_ID} simulated failure")

    # Tokenize imput text
    inputs = tokenizer(request.input, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        # Extract CLS token vector as output
        cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze().tolist()

    return {
        "worker_id": WORKER_ID,
        "model": MODEL_NAME,
        "input": request.input,
        "output_cls_vector": cls_embedding[:5]  # Return first 5 dimensions outpt for brevity
    }

@app.get("/health")
async def health():
    return {"status": "ok", "worker_id": WORKER_ID}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 9001))
    uvicorn.run("w1-BERT:app", host="0.0.0.0", port=port)

# BERT worker: 0.0.0.0:9001, text classification and embedding