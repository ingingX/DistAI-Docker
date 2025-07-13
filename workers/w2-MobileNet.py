import random
import asyncio
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import torch
from torchvision import models, transforms
from PIL import Image
import base64
from io import BytesIO

# Init model and environment variables
MODEL_NAME = "mobilenet_v3_small"
WORKER_ID = os.getenv("WORKER_ID", "w2-mobilenet")
FAIL_RATE = float(os.getenv("FAIL_RATE", "0.2"))
DELAY_RANGE = (0.1, 1.0)

print(f"[{WORKER_ID}] Loading model {MODEL_NAME}...")
model = models.mobilenet_v3_small(pretrained=True)
model.eval()
print(f"[{WORKER_ID}] Model loaded.")

# Define image preprocess
preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
])

app = FastAPI()

class InferenceRequest(BaseModel):
    image_base64: str

@app.post("/infer")
async def infer(request: InferenceRequest):
    await asyncio.sleep(random.uniform(*DELAY_RANGE))

    if random.random() < FAIL_RATE:
        raise HTTPException(status_code=500, detail=f"{WORKER_ID} simulated failure")

    try:
        image_data = base64.b64decode(request.image_base64)
        image = Image.open(BytesIO(image_data)).convert("RGB")
        input_tensor = preprocess(image).unsqueeze(0)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image data")

    with torch.no_grad():
        output = model(input_tensor)
        predicted_class = torch.argmax(output, dim=1).item()

    return {
        "worker_id": WORKER_ID,
        "model": MODEL_NAME,
        "predicted_class": predicted_class
    }

@app.get("/health")
async def health():
    return {"status": "ok", "worker_id": WORKER_ID}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 9002))
    uvicorn.run("w2-MobileNet:app", host="0.0.0.0", port=port)

# MobileNet worker: 0.0.0.0:9002, image classification