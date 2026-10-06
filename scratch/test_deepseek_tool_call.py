import urllib.request
import json
import os
import time
from dotenv import load_dotenv

load_dotenv('.env')

key = os.getenv('NVIDIA_API_KEY')
base_url = os.getenv('NVIDIA_BASE_URL', 'https://integrate.api.nvidia.com/v1')
model = os.getenv('NVIDIA_MODEL', 'deepseek-ai/deepseek-v4.1-flash')

payload = {
    'model': model,
    'messages': [
        {'role': 'user', 'content': 'Please get the weather in Paris by invoking the get_weather function.'}
    ],
    'tools': [{
        'type': 'function',
        'function': {
            'name': 'get_weather',
            'description': 'Get the current weather for a city',
            'parameters': {
                'type': 'object',
                'properties': {'city': {'type': 'string', 'description': 'The city name'}},
                'required': ['city']
            }
        }
    }],
    'tool_choice': 'auto',
    'max_tokens': 2048,
    'stream': True
}

req = urllib.request.Request(
    f"{base_url}/chat/completions",
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json'
    }
)

start = time.time()
print(f"Testing live tool call against {model} at {base_url}...", flush=True)

try:
    with urllib.request.urlopen(req, timeout=90) as resp:
        print(f"HTTP {resp.status} received in {time.time()-start:.2f}s. Parsing stream chunks...", flush=True)
        tool_calls = []
        reasoning_chars = 0
        content_chars = 0
        for line in resp:
            line_str = line.decode('utf-8').strip()
            if line_str.startswith('data: ') and line_str != 'data: [DONE]':
                chunk = json.loads(line_str[6:])
                delta = chunk['choices'][0]['delta']
                if delta.get('tool_calls'):
                    tool_calls.append(delta['tool_calls'])
                    print(f"\n[TOOL CALL CHUNK]: {delta['tool_calls']}", flush=True)
                if delta.get('reasoning_content'):
                    reasoning_chars += len(delta['reasoning_content'])
                    if reasoning_chars % 100 == 0:
                        print(f"[Reasoning... {reasoning_chars} chars]", flush=True)
                if delta.get('content'):
                    content_chars += len(delta['content'])
                    print(delta['content'], end='', flush=True)

        print(f"\nStream completed in {time.time()-start:.2f}s!")
        print(f"Reasoning length: {reasoning_chars} chars, Content length: {content_chars} chars")
        print(f"Total tool call chunks captured: {len(tool_calls)}")
except Exception as e:
    print(f"\nRequest failed in {time.time()-start:.2f}s: {e}", flush=True)
