import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv(".env")

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
api_key = os.environ.get("NVIDIA_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "text/event-stream",
    "Content-Type": "application/json"
}

tools = [{
    "type": "function",
    "function": {
        "name": "get_stock_price",
        "description": "Get current stock price for a symbol",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol, e.g. NVDA"}
            },
            "required": ["symbol"]
        }
    }
}]

payload = {
    "model": "moonshotai/kimi-k3",
    "messages": [
        {"role": "user", "content": "What is the stock price of NVDA? Call the get_stock_price tool."}
    ],
    "tools": tools,
    "tool_choice": "auto",
    "max_tokens": 1024,
    "stream": True,
}

print("Testing tool calling with moonshotai/kimi-k3...", flush=True)
start = time.time()
try:
    resp = requests.post(invoke_url, headers=headers, json=payload, stream=True, timeout=90)
    print("HTTP Status Code:", resp.status_code, flush=True)
    if resp.status_code != 200:
        print("Error text:", resp.text, flush=True)
    else:
        tool_call_chunks = []
        reasoning_chunks = []
        content_chunks = []
        for line in resp.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: ") and decoded != "data: [DONE]":
                    chunk = json.loads(decoded[6:])
                    delta = chunk["choices"][0]["delta"]
                    if delta.get("tool_calls"):
                        tool_call_chunks.append(delta["tool_calls"])
                        print("\n[TOOL CALL]:", delta["tool_calls"], flush=True)
                    elif delta.get("reasoning_content"):
                        reasoning_chunks.append(delta["reasoning_content"])
                        if len(reasoning_chunks) % 10 == 0:
                            print("[R]", end="", flush=True)
                    elif delta.get("content"):
                        content_chunks.append(delta["content"])
                        print(delta["content"], end="", flush=True)
        print(f"\n\nDone in {time.time()-start:.2f}s!")
        print(f"Tool call chunks: {len(tool_call_chunks)}")
        print(f"Reasoning chunks: {len(reasoning_chunks)}")
except Exception as e:
    print(f"Failed in {time.time()-start:.2f}s: {e}", flush=True)
