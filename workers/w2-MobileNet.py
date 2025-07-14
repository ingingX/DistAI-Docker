"""
MobileNet Worker Service

Exposes localhost 9002 port.
input image and returns the highest logit from the MobileNet classifier.

Model used: torchvision.models.mobilenet_v3_small (pretrained)
"""

from flask import Flask, request, jsonify
from torchvision import models, transforms
from PIL import Image
import torch, base64, io, random, time

# init flask
app = Flask(__name__)

# init model
model = models.mobilenet_v3_small(pretrained=True)
model.eval()

# define '/infer' to handle POST requests
@app.route("/infer", methods=["POST"])
def infer():
    # Download image and convert to base64
    img_b64 = request.json.get("image_base64", "")
    img_bytes = base64.b64decode(img_b64)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    #preprocess image text
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
    ])
    input_tensor = preprocess(img).unsqueeze(0)
    # run model
    with torch.no_grad():
        time.sleep(random.uniform(0, 2)) # Simulate delay
        output = model(input_tensor)
    return jsonify({"max_logit": output.max().item()})

# Health check
@app.route("/status")
def status():
    return jsonify({"status": "online"})

# main
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9002)