import os
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".env")
api_key = os.getenv("FREELLMAPI_KEY")
base_url = os.getenv("FREELLMAPI_BASE_URL", "http://localhost:3001/v1")

print(f"Connecting to FreeLLMAPI at {base_url}")
masked_key = (api_key[:8] + "..." + api_key[-4:]) if api_key and len(api_key) > 12 else "NONE"
print(f"Loaded key: {masked_key}")

client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)

# 1. Basic test provided by user
print("\n--- Test 1: Chat Completion (model='auto') ---")
t0 = time.time()
try:
    raw_resp = client.chat.completions.with_raw_response.create(
        model="auto",
        messages=[{"role": "user", "content": "Summarise the fall of Rome in one sentence."}],
        timeout=45.0,
    )
    elapsed = time.time() - t0
    resp = raw_resp.parse()
    print(f"SUCCESS ({elapsed:.2f}s):")
    print("Content:", resp.choices[0].message.content)
    print("Model reported:", resp.model)
    print("Routed via:", raw_resp.headers.get("x-routed-via", "N/A"))
except Exception as e:
    elapsed = time.time() - t0
    print(f"FAILED ({elapsed:.2f}s): {type(e).__name__}: {e}")

# 2. Tool Calling test
test_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "The name of the city"}
                },
                "required": ["city"],
            },
        },
    }
]

print("\n--- Test 2: Native Tool Calling (model='auto') ---")
t0 = time.time()
try:
    raw_tool = client.chat.completions.with_raw_response.create(
        model="auto",
        messages=[{"role": "user", "content": "What is the current weather in Tokyo?"}],
        tools=test_tools,
        tool_choice="auto",
        timeout=45.0,
    )
    elapsed = time.time() - t0
    tool_resp = raw_tool.parse()
    print(f"SUCCESS ({elapsed:.2f}s):")
    print("Model reported:", tool_resp.model)
    print("Routed via:", raw_tool.headers.get("x-routed-via", "N/A"))
    print("Tool calls:", tool_resp.choices[0].message.tool_calls)
    print("Content:", tool_resp.choices[0].message.content)
except Exception as e:
    elapsed = time.time() - t0
    print(f"FAILED ({elapsed:.2f}s): {type(e).__name__}: {e}")
