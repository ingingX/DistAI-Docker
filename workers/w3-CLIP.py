"""
CLIP Worker Service

Exposes localhost 9003 port.
input both text and image and returns similarity score from the CLIP.

Model used: openai/clip-vit-base-patch32
"""

from flask import Flask, request, jsonify
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch, base64, io, random, time

# init flask
app = Flask(__name__)

# init model and processor
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")

# define '/infer' to handle POST requests
@app.route("/infer", methods=["POST"])
def infer():
    # Download image and convert to base64
    img_b64 = request.json.get("image_base64", "")
    img_bytes = base64.b64decode(img_b64)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    # preprocess input text
    text = request.json.get("text", "a photo")
    # create inputs for CLIP
    inputs = processor(text=[text], images=img, return_tensors="pt", padding=True)
    # run model
    with torch.no_grad():
        time.sleep(random.uniform(0, 2))
        outputs = model(**inputs)
    return jsonify({"logit_score": outputs.logits_per_image.item()})

# Health check
@app.route("/status")
def status():
    return jsonify({"status": "online"})

# main
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9003)