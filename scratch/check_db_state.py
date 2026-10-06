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
r = requests.get("http://localhost:8000/api/v1/workspaces/", headers=headers)
print("Workspaces status:", r.status_code)
workspaces = r.json()
print("Workspaces found:", len(workspaces))
for w in workspaces:
    print(f" - ID: {w['id']}, Name: {w['name']}")
    r_conv = requests.get(f"http://localhost:8000/api/v1/workspaces/{w['id']}/conversations/", headers=headers)
    print(f"   Conversations ({len(r_conv.json())}):")
    for c in r_conv.json():
        print(f"     * ID: {c['id']}, Title: {c['title']}")
