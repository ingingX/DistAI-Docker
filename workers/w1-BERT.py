"""
BERT Worker Service

Exposes localhost 9001 port.
input text and returns sum of the BERT embedding.

Model used: prajwal1/bert-tiny
"""

from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModel
import torch, time, random

# init flask
app = Flask(__name__)

# init model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("prajjwal1/bert-tiny")
model = AutoModel.from_pretrained("prajjwal1/bert-tiny")

# define '/infer' to handle POST requests
@app.route("/infer", methods=["POST"])
def infer():
    #preprocess input text
    data = request.json.get("text", "")
    inputs = tokenizer(data, return_tensors="pt")
    # run model
    with torch.no_grad():
        time.sleep(random.uniform(0, 2))  # Simulate delay
        outputs = model(**inputs)
    return jsonify({"embedding_sum": outputs.last_hidden_state.sum().item()})

# Health check
@app.route("/status")
def status():
    return jsonify({"status": "online"})

# main
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9001)