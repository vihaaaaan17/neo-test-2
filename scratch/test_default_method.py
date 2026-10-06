import os
import time
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model

load_dotenv(".env")
api_key = os.getenv("NVIDIA_API_KEY")
base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

os.environ["OPENAI_API_BASE"] = base_url
os.environ["OPENAI_BASE_URL"] = base_url
os.environ["OPENAI_API_KEY"] = api_key

class ResearchQuestion(BaseModel):
    research_brief: str = Field(description="Brief summarizing the research topic")

configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)

# Test default with_structured_output (NO method argument, exactly like upstream ODR)
test_model = (
    configurable_model
    .with_structured_output(ResearchQuestion)
    .with_config({
        "model": "openai:z-ai/glm-5.3-flash",
        "max_tokens": 4096,
        "api_key": api_key,
    })
)

t0 = time.time()
try:
    res = test_model.invoke("Briefly state the research brief on solid state battery cathode materials")
    elapsed = time.time() - t0
    print(f"DEFAULT METHOD SUCCESS in {elapsed:.2f}s:")
    print("Result:", type(res), res)
except Exception as e:
    elapsed = time.time() - t0
    print(f"DEFAULT METHOD FAILED in {elapsed:.2f}s: {type(e).__name__}: {e}")
