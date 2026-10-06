import requests
import jwt
import time

user_id = "00000000-0000-0000-0000-000000000001"
secret = "super-secret-jwt-token-for-supabase-local-dev-only"
token = jwt.encode(
    {"sub": user_id, "aud": "authenticated", "iat": int(time.time()), "exp": int(time.time()) + 3600*24*7},
    secret,
    algorithm="HS256"
)

headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
ws_id = "a12c1fa3-d3a6-4ffd-a0b1-77b8492f8ce5"

r_ws = requests.get(f"http://localhost:8000/api/v1/workspaces/{ws_id}", headers=headers)
print("Workspace status:", r_ws.status_code, r_ws.json())

r_conv = requests.get(f"http://localhost:8000/api/v1/workspaces/{ws_id}/conversations/", headers=headers)
print("Conversations status:", r_conv.status_code, r_conv.json())
