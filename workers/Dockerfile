FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt
COPY w1-BERT.py .
COPY w2-MobileNet.py .
COPY w3-CLIP.py .
CMD ["python", "w1-BERT.py"]