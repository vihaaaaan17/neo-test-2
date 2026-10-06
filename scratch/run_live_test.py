"""
External Verification Runner for NeosisLM with z-ai/glm-5.3-flash
Zero changes to core codebase. Validates that the model swap is active,
chat reasoning works, and function calling / structured output succeeds.
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv(".env")

def test_environment():
    print("=" * 60)
    print("1. Environment Configuration Check")
    print("=" * 60)
    provider = os.getenv("LLM_PROVIDER")
    model = os.getenv("NVIDIA_MODEL")
    base_url = os.getenv("NVIDIA_BASE_URL")
    api_key = os.getenv("NVIDIA_API_KEY")

    print(f"  LLM_PROVIDER: {provider}")
    print(f"  NVIDIA_MODEL: {model}")
    print(f"  NVIDIA_BASE_URL: {base_url}")
    print(f"  NVIDIA_API_KEY: {'[SET]' if api_key else '[MISSING]'}")

    assert provider == "nvidia", f"Expected LLM_PROVIDER=nvidia, got {provider}"
    assert model == "z-ai/glm-5.3-flash", f"Expected NVIDIA_MODEL=z-ai/glm-5.3-flash, got {model}"
    print("  -> Configuration verified: z-ai/glm-5.3-flash is active.")

def test_chat():
    print("\n" + "=" * 60)
    print("2. Chat & Reasoning Check")
    print("=" * 60)
    from openai import OpenAI
    client = OpenAI(
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        api_key=os.getenv("NVIDIA_API_KEY")
    )
    t0 = time.time()
    resp = client.chat.completions.create(
        model=os.getenv("NVIDIA_MODEL"),
        messages=[
            {"role": "user", "content": "What are the two major classes of solid state battery electrolytes? Answer in 2 short bullet points."}
        ],
        temperature=0.2,
        max_tokens=2048,
    )
    elapsed = time.time() - t0
    print(f"  -> SUCCESS ({elapsed:.2f}s)")
    # Encode safely for Windows console
    safe_text = resp.choices[0].message.content.encode("ascii", "replace").decode("ascii")
    print(f"  -> Response:\n{safe_text}")

def test_tool_calling():
    print("\n" + "=" * 60)
    print("3. Research Engine Tool Calling & Structured Output Check")
    print("=" * 60)
    from pydantic import BaseModel, Field
    from langchain.chat_models import init_chat_model

    class ResearchBrief(BaseModel):
        focus_area: str = Field(description="Primary research focus area")
        key_questions: list[str] = Field(description="Key scientific research questions")

    os.environ["OPENAI_API_BASE"] = os.getenv("NVIDIA_BASE_URL")
    os.environ["OPENAI_BASE_URL"] = os.getenv("NVIDIA_BASE_URL")
    os.environ["OPENAI_API_KEY"] = os.getenv("NVIDIA_API_KEY")

    configurable_model = init_chat_model(
        configurable_fields=("model", "max_tokens", "api_key"),
    )

    model_pipeline = (
        configurable_model
        .with_structured_output(ResearchBrief, method="function_calling")
        .with_config({
            "model": f"openai:{os.getenv('NVIDIA_MODEL')}",
            "max_tokens": 2048,
            "api_key": os.getenv("NVIDIA_API_KEY"),
        })
    )

    t0 = time.time()
    result = model_pipeline.invoke("Decompose a research plan on sulfide vs oxide solid electrolytes interface impedance.")
    elapsed = time.time() - t0
    print(f"  -> SUCCESS ({elapsed:.2f}s)")
    print(f"  -> Focus Area: {result.focus_area}")
    print(f"  -> Key Questions ({len(result.key_questions)}):")
    for q in result.key_questions:
        safe_q = q.encode("ascii", "replace").decode("ascii")
        print(f"     - {safe_q}")

if __name__ == "__main__":
    try:
        test_environment()
        test_chat()
        test_tool_calling()
        print("\n" + "=" * 60)
        print("ALL CHECKS PASSED: Model is ready for live NeosisLM execution!")
        print("=" * 60)
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        sys.exit(1)
