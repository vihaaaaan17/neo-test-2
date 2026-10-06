import os
import time
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model

load_dotenv(".env")
api_key = os.getenv("NVIDIA_API_KEY")
base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")

# Make sure langchain_openai knows where to route
os.environ["OPENAI_API_BASE"] = base_url
os.environ["OPENAI_BASE_URL"] = base_url
os.environ["OPENAI_API_KEY"] = api_key

class ResearchQuestion(BaseModel):
    research_brief: str = Field(description="Brief summarizing the research topic")

print("Initializing configurable_model with init_chat_model...")
configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)

model_id = "openai:z-ai/glm-5.3-flash"
print(f"Configuring model with {model_id} and base_url={base_url}...")

# Test structured output as ODR does
test_model = (
    configurable_model
    .with_structured_output(ResearchQuestion, method="function_calling")
    .with_config({
        "model": model_id,
        "max_tokens": 1024,
        "api_key": api_key,
    })
)

t0 = time.time()
try:
    res = test_model.invoke("Synthesize a brief on solid state battery cathode materials")
    elapsed = time.time() - t0
    print(f"SUCCESS in {elapsed:.2f}s:")
    print("Result:", type(res), res)
except Exception as e:
    elapsed = time.time() - t0
    print(f"FAILED in {elapsed:.2f}s: {type(e).__name__}: {e}")
