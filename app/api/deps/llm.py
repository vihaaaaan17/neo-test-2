import asyncio
from typing import Callable, Awaitable

async def mock_llm_call(prompt: str) -> str:
    # This is a stub. In a real system, this would call LiteLLM or OpenAI.
    return '{"answer": "Mock answer based on context", "evidence": []}'

async def mock_embed_call(text: str) -> list[float]:
    # This is a stub. Returns a zero vector.
    return [0.0] * 1536

def get_llm_gateway() -> Callable[[str], Awaitable[str]]:
    return mock_llm_call

def get_embed_gateway() -> Callable[[str], Awaitable[list[float]]]:
    return mock_embed_call
