import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".env")
api_key = os.getenv("FREELLMAPI_KEY")
base_url = os.getenv("FREELLMAPI_BASE_URL", "http://localhost:3001/v1")

client = OpenAI(base_url=base_url, api_key=api_key)

try:
    models = client.models.list()
    print(f"Total models available: {len(models.data)}")
    for m in models.data[:25]:
        print(f" - {m.id}")
except Exception as e:
    print(f"Error listing models: {e}")
