import os
import time
import requests
import json
from dotenv import load_dotenv

load_dotenv(".env")
api_key = os.getenv("NVIDIA_API_KEY")
invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "text/event-stream",
    "Content-Type": "application/json"
}

payload = {
    "model": "z-ai/glm-5.3",
    "messages": [
        {"role": "user", "content": "Hi"}
    ],
    "max_tokens": 64,
    "temperature": 0.5,
    "stream": True
}

print("--- Test 1: Testing z-ai/glm-5.3 with stream=True ---")
t0 = time.time()
try:
    response = requests.post(invoke_url, headers=headers, json=payload, stream=True, timeout=120)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    first_chunk_time = None
    chunks = []
    for line in response.iter_lines():
        if line:
            if first_chunk_time is None:
                first_chunk_time = time.time() - t0
                print(f"First chunk received in {first_chunk_time:.2f}s!")
            decoded = line.decode("utf-8")
            print("Chunk:", decoded[:100])
            chunks.append(decoded)
            if len(chunks) >= 5:
                break
    print(f"Total time: {time.time() - t0:.2f}s")
except Exception as e:
    print(f"Exception ({time.time() - t0:.2f}s): {type(e).__name__}: {e}")

# Check non-streaming with raw headers
print("\n--- Test 2: Testing z-ai/glm-5.3 with stream=False (inspecting raw response) ---")
headers_json = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}
payload["stream"] = False
t0 = time.time()
try:
    response = requests.post(invoke_url, headers=headers_json, json=payload, timeout=120)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Body: {response.text[:500]}")
except Exception as e:
    print(f"Exception ({time.time() - t0:.2f}s): {type(e).__name__}: {e}")
