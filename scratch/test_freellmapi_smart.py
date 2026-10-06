import os
import time
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

load_dotenv(".env")
api_key = os.getenv("FREELLMAPI_KEY")
base_url = os.getenv("FREELLMAPI_BASE_URL", "http://localhost:3001/v1")

class SearchQuery(BaseModel):
    query: str = Field(description="Search query string")
    rationale: str = Field(description="Why this query was chosen")

candidates = ["gemini-2.5-flash", "claude-sonnet-4-5", "qwen3.8-27b"]

for model in candidates:
    print(f"\n==========================================")
    print(f"Testing model on FreeLLMAPI: {model}")
    print(f"==========================================")
    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0.1,
        max_tokens=1024,
    )
    t0 = time.time()
    try:
        structured_llm = llm.with_structured_output(SearchQuery, method="function_calling")
        res = structured_llm.invoke("Find recent breakthroughs in solid electrolyte interface impedance")
        elapsed = time.time() - t0
        print(f"SUCCESS in {elapsed:.2f}s:")
        print(" -> Output:", res)
    except Exception as e:
        elapsed = time.time() - t0
        print(f"FAILED in {elapsed:.2f}s: {e}")
