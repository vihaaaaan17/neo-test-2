import os
import time
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

load_dotenv(".env")
api_key = os.getenv("FREELLMAPI_KEY")
base_url = os.getenv("FREELLMAPI_BASE_URL", "http://localhost:3001/v1")

print(f"Testing LangChain with FreeLLMAPI at {base_url} (model='auto')...")

llm = ChatOpenAI(
    model="auto",
    api_key=api_key,
    base_url=base_url,
    temperature=0.1,
    max_tokens=1024,
)

# Test 1: bind_tools with Pydantic
class SearchQuery(BaseModel):
    query: str = Field(description="Search query string")
    rationale: str = Field(description="Why this query was chosen")

print("\n--- Test 1: LangChain bind_tools ---")
t0 = time.time()
try:
    llm_with_tools = llm.bind_tools([SearchQuery])
    res = llm_with_tools.invoke("Research the latest solid state battery cathode materials")
    elapsed = time.time() - t0
    print(f"SUCCESS in {elapsed:.2f}s")
    print("tool_calls:", res.tool_calls)
    print("content:", res.content)
except Exception as e:
    elapsed = time.time() - t0
    print(f"FAILED in {elapsed:.2f}s: {e}")

# Test 2: with_structured_output (function_calling)
print("\n--- Test 2: LangChain with_structured_output (function_calling) ---")
t0 = time.time()
try:
    structured_llm = llm.with_structured_output(SearchQuery, method="function_calling")
    res_struct = structured_llm.invoke("Find recent breakthroughs in solid electrolyte interface impedance")
    elapsed = time.time() - t0
    print(f"SUCCESS in {elapsed:.2f}s")
    print("Structured Result:", type(res_struct), res_struct)
except Exception as e:
    elapsed = time.time() - t0
    print(f"FAILED in {elapsed:.2f}s: {e}")
