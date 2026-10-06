import os
import json
import time
from dotenv import load_dotenv
import requests

load_dotenv(".env")

api_key = os.getenv("NVIDIA_API_KEY")
invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

print("=" * 60)
print("TEST 1: Testing moonshotai/kimi-k3 basic text generation & streaming")
print("=" * 60)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "text/event-stream",
    "Content-Type": "application/json"
}

payload = {
    "model": "moonshotai/kimi-k3",
    "messages": [
        {"role": "user", "content": "Explain solid-state battery electrolytes in 2 sentences."}
    ],
    "max_tokens": 512,
    "temperature": 0.3,
    "stream": True
}

start = time.time()
try:
    resp = requests.post(invoke_url, headers=headers, json=payload, stream=True, timeout=30)
    print(f"HTTP Status: {resp.status_code}")
    if resp.status_code != 200:
        print("Error Response:", resp.text)
    else:
        print("Streaming response:")
        for line in resp.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: ") and decoded != "data: [DONE]":
                    try:
                        chunk = json.loads(decoded[6:])
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta and delta["content"]:
                            print(delta["content"], end="", flush=True)
                    except Exception:
                        pass
        print(f"\n\nTest 1 completed in {time.time()-start:.2f}s!")
except Exception as e:
    print(f"Test 1 Failed: {e}")

print("\n" + "=" * 60)
print("TEST 2: Testing moonshotai/kimi-k3 TOOL CALLING capabilities")
print("=" * 60)

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "The city name"}
            },
            "required": ["city"]
        }
    }
}]

payload_tools = {
    "model": "moonshotai/kimi-k3",
    "messages": [
        {"role": "user", "content": "What is the weather in Tokyo right now? Call the get_weather function."}
    ],
    "tools": tools,
    "tool_choice": "auto",
    "max_tokens": 512,
    "stream": True
}

start = time.time()
try:
    resp_tool = requests.post(invoke_url, headers=headers, json=payload_tools, stream=True, timeout=30)
    print(f"HTTP Status: {resp_tool.status_code}")
    if resp_tool.status_code != 200:
        print("Error Response:", resp_tool.text)
    else:
        print("Reading stream with tools:")
        tool_calls = []
        for line in resp_tool.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: ") and decoded != "data: [DONE]":
                    try:
                        chunk = json.loads(decoded[6:])
                        delta = chunk["choices"][0]["delta"]
                        if "tool_calls" in delta and delta["tool_calls"]:
                            tool_calls.append(delta["tool_calls"])
                            print(f"\n[TOOL CALL DETECTED]: {delta['tool_calls']}", flush=True)
                        elif "content" in delta and delta["content"]:
                            print(delta["content"], end="", flush=True)
                    except Exception:
                        pass
        print(f"\n\nTest 2 completed in {time.time()-start:.2f}s!")
        print(f"Total tool call chunks detected: {len(tool_calls)}")
except Exception as e:
    print(f"Test 2 Failed: {e}")
