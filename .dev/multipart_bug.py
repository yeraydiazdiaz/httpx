import requests
import uuid
import subprocess
import json
import os
from pathlib import Path
import httpx


url = "https://httpbin.org/post"

event = "ASDGASFDASDF"
payload = {"event": "event", "confidence": 95}
image_path = ".dev/avatar-circle.png"


files = {
    "upload-file": (None, "text content", "application/json"),
    "image": ("avatar", open(image_path, "rb"), "application/octet-stream"),
    # 'image1': (os.path.basename(newName), open(newName, 'rb'), 'application/octet-stream'),
    # 'image2': (os.path.basename(newName), open(newName, 'rb'), 'application/octet-stream')
}

# Do the HTTP POST
r = httpx.post(url, files=files)
print(r.text)
r = requests.post(url, files=files)
print(r.text)
