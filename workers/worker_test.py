import requests
import base64

# 下载测试图片
url = "https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png"
resp = requests.get(url)
img_bytes = resp.content

# 转base64
b64 = base64.b64encode(img_bytes).decode()

response = requests.post("http://localhost:9002/infer", json={"image_base64": b64})
print(response.json())
