import os
import sys
import time
from dotenv import load_dotenv

# 1. Load keys directly from .env or .env.ui
load_dotenv(".env")
load_dotenv(".env.ui")

api_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1"
model = os.environ.get("NVIDIA_MODEL") or "deepseek-ai/deepseek-v4.1-flash"

if not api_key:
    print("ERROR: No NVIDIA_API_KEY or OPENAI_API_KEY found.")
    sys.exit(1)

masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
print(f"Connecting to: {base_url}")
print(f"Target Model:  {model}")
print(f"Using Key:     {masked_key}")
print("=" * 60)

from openai import OpenAI
client = OpenAI(base_url=base_url, api_key=api_key)

# We ask a complex multi-step reasoning question to prove it's a live thinking model
prompt = (
    "Answer the following three questions clearly:\n"
    "1. Logic puzzle: A farmer has 17 sheep, all but 9 die. Then he buys twice as many as survived. "
    "How many sheep does the farmer have now? Explain the arithmetic.\n"
    "2. Technical question: In 2 sentences, explain how an append-only timeline epoch fence "
    "prevents split-brain state in distributed systems.\n"
    "3. Creative output: Write a haiku about autonomous deep research agents."
)

print(f"\nUser Prompt:\n{prompt}\n")
print("-" * 60)
print("Sending live request (streaming tokens)...")
print("-" * 60)

start_time = time.time()
try:
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a precise, highly intelligent AI assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=512,
        temperature=0.3,
        stream=True,
    )

    full_response = []
    for chunk in stream:
        delta = chunk.choices[0].delta
        # Check for reasoning content or standard content
        reasoning = getattr(delta, "reasoning_content", None)
        if reasoning:
            # Print reasoning if available
            sys.stdout.write(reasoning)
            sys.stdout.flush()
        if delta.content:
            sys.stdout.write(delta.content)
            sys.stdout.flush()
            full_response.append(delta.content)

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "-" * 60)
    print(f"Completed in {elapsed}s via real NVIDIA DeepSeek inference!")
    print("=" * 60)

except Exception as e:
    print(f"\nError from live API: {e}")
    sys.exit(1)
