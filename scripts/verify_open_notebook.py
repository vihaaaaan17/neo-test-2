import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

async def verify():
    load_dotenv()
    
    print("=== NeosisLM: Open Notebook Verification ===")
    
    # 1. Check for required credentials
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or "your-google-api-key" in api_key:
        print("❌ ERROR: Valid GOOGLE_API_KEY is missing from .env.")
        print("   Open Notebook requires an LLM provider key to embed text.")
        sys.exit(1)
    else:
        print("✅ Credentials: GOOGLE_API_KEY found.")
        
    on_url = "http://localhost:5055"
    password = os.getenv("OPEN_NOTEBOOK_PASSWORD")
    
    headers = {}
    if password:
        headers["Authorization"] = f"Bearer {password}"
        
    async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
        # 2. Check Health
        print("\n[1/3] Checking Open Notebook health endpoint...")
        try:
            res = await client.get(f"{on_url}/health")
            if res.status_code == 200:
                print(f"✅ Health check passed: {res.json()}")
            else:
                print(f"❌ Health check failed: HTTP {res.status_code} - {res.text}")
                sys.exit(1)
        except httpx.RequestError as e:
            print(f"❌ Connection failed: Could not connect to Open Notebook at {on_url}.")
            print("   Is the docker-compose stack running?")
            print(f"   Error: {e}")
            sys.exit(1)

        # 3. Simulate text ingestion
        print("\n[2/3] Simulating text/markdown ingestion...")
        data = {
            "title": "NeosisLM Verification Test",
            "content": "This is a test note to verify the integration between NeosisLM and Open Notebook.",
        }
        try:
            res = await client.post(f"{on_url}/api/notes", json=data)
            if res.status_code == 200:
                note_id = res.json().get("id")
                print(f"✅ Ingestion successful. Note ID: {note_id}")
            else:
                print(f"❌ Ingestion failed: HTTP {res.status_code} - {res.text}")
        except Exception as e:
            print(f"❌ Ingestion request failed: {e}")

        # 4. Search / Ask Query
        print("\n[3/3] Executing search query...")
        query_data = {
            "query": "verify integration",
            "type": "text",
            "limit": 5,
            "search_sources": True,
            "search_notes": True
        }
        try:
            res = await client.post(f"{on_url}/api/search", json=query_data)
            if res.status_code == 200:
                results = res.json().get("results", [])
                print(f"✅ Search successful. Found {len(results)} results.")
            else:
                print(f"❌ Search failed: HTTP {res.status_code} - {res.text}")
        except Exception as e:
            print(f"❌ Search request failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
