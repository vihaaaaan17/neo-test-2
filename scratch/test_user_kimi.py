import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
stream = True

api_key = os.environ.get("NVIDIA_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "text/event-stream" if stream else "application/json",
}

payload = {
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "What is in this image?"
        },
        {
          "type": "image_url",
          "image_url": {
            "url": "https://assets.ngc.nvidia.com/products/api-catalog/phi-3-5-vision/example1b.jpg"
          }
        }
      ]
    }
  ],
  "model": "moonshotai/kimi-k3",
  "max_tokens": 16384,
  "seed": 0,
  "stream": stream,
  "temperature": 1,
  "reasoning_effort": "max"
}

print("Sending request to moonshotai/kimi-k3...", flush=True)
try:
    response = requests.post(invoke_url, headers=headers, json=payload, stream=stream, timeout=120)
    print("Response status code:", response.status_code, flush=True)
    if stream:
        line_count = 0
        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                print(decoded, flush=True)
                line_count += 1
                if line_count > 10:
                    print("... (more stream lines received successfully)", flush=True)
                    break
    else:
        print(response.json(), flush=True)
except Exception as e:
    print("Error:", e, flush=True)
