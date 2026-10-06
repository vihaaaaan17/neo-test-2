import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")
api_key = os.getenv("NVIDIA_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
}

r = requests.get("https://integrate.api.nvidia.com/v1/models", headers=headers)
if r.status_code == 200:
    data = r.json()
    glm_models = [m for m in data.get("data", []) if "glm" in m.get("id", "").lower()]
    print("GLM models found in NVIDIA NIM catalog:")
    for m in glm_models:
        print(f" - id: {m.get('id')}, owned_by: {m.get('owned_by')}")
else:
    print(f"Failed to list models: {r.status_code} - {r.text}")
