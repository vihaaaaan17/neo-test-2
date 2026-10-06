import json
import httpx
import jwt
import time

user_id = "00000000-0000-0000-0000-000000000001"
secret = "super-secret-jwt-token-for-supabase-local-dev-only"
token = jwt.encode(
    {"sub": user_id, "aud": "authenticated", "iat": int(time.time()), "exp": int(time.time()) + 3600*24*7},
    secret,
    algorithm="HS256"
)

base_url = "http://localhost:8000"
workspace_id = "a12c1fa3-d3a6-4ffd-a0b1-77b8492f8ce5"
conversation_id = "8368832f-e723-406a-8303-c0c412932b73"

headers = {
    "Accept": "text/event-stream",
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "NeosisLM-IntegrationTestbed/1.0"
}

body = {
    "mode": "ground",
    "message": "What is the status of the workspace knowledge?",
}

print(f"Submitting Ground Mode turn via SSE stream to {base_url}...")
url = f"{base_url}/api/v1/workspaces/{workspace_id}/conversations/{conversation_id}/turns?stream=true"

t0 = time.time()
with httpx.Client(timeout=60.0) as client:
    with client.stream("POST", url, headers=headers, json=body) as response:
        print(f"HTTP Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        current_event = None
        current_data = None
        for line in response.iter_lines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("event:"):
                current_event = line.replace("event:", "").strip()
            elif line.startswith("data:"):
                current_data = line.replace("data:", "").strip()
                print(f"[{time.time()-t0:.2f}s] Event: {current_event} | Data: {current_data[:120]}")
                if current_event in ("turn.completed", "done", "turn.failed", "error"):
                    print(f"Terminal event reached: {current_event}")
                    break
