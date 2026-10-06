import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".env")
api_key = os.getenv("NVIDIA_API_KEY")
base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

client = OpenAI(base_url=base_url, api_key=api_key)

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

models_to_test = ["z-ai/glm-5.3", "z-ai/glm-5.3-flash"]

for model in models_to_test:
    print(f"\n==========================================")
    print(f"Testing model: {model}")
    print(f"==========================================")

    # 1. Basic Chat
    print(f"\n[1] Basic Chat Completion:")
    start_t = time.time()
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Which number is larger, 9.11 or 9.8? Answer concisely."}
            ],
            temperature=0.5,
            max_tokens=256,
            stream=False,
            timeout=30.0,
        )
        elapsed = time.time() - start_t
        msg = completion.choices[0].message
        print(f"  -> SUCCESS ({elapsed:.2f}s)")
        print(f"  -> Response: {msg.content}")
    except Exception as e:
        elapsed = time.time() - start_t
        print(f"  -> FAILED ({elapsed:.2f}s): {type(e).__name__}: {e}")

    # 2. Native Tool Calling
    print(f"\n[2] Native Tool Calling (tools=[get_weather]):")
    start_t = time.time()
    try:
        tool_completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "What is the weather in Tokyo right now?"}
            ],
            tools=test_tools,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=512,
            stream=False,
            timeout=40.0,
        )
        elapsed = time.time() - start_t
        msg = tool_completion.choices[0].message
        print(f"  -> SUCCESS ({elapsed:.2f}s)")
        print(f"  -> Content: {msg.content}")
        print(f"  -> Tool Calls: {msg.tool_calls}")
    except Exception as e:
        elapsed = time.time() - start_t
        print(f"  -> FAILED ({elapsed:.2f}s): {type(e).__name__}: {e}")
