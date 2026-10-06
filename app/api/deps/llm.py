import logging
import os
from typing import Callable, Awaitable

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768  # must match document_blocks.embedding Vector(768)


def _resolve_llm_credentials() -> tuple[str, str | None, str]:
    """Resolve (api_key, base_url, model) for the OpenAI-compatible gateway."""
    if (os.environ.get("LLM_PROVIDER") or settings.LLM_PROVIDER or "openai").lower() == "nvidia" or (
        not os.environ.get("OPENAI_API_KEY") and os.environ.get("NVIDIA_API_KEY")
    ):
        api_key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("NVIDIA_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://integrate.api.nvidia.com/v1"
        model = os.environ.get("NVIDIA_MODEL") or os.environ.get("OPENAI_MODEL") or "deepseek-ai/deepseek-v4.1-flash"
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        model = os.environ.get("OPENAI_MODEL") or "gpt-4o"
    if not api_key:
        raise RuntimeError("Neither OPENAI_API_KEY nor NVIDIA_API_KEY is configured.")
    if base_url and base_url.endswith("/chat/completions"):
        base_url = base_url[: -len("/chat/completions")]
    return api_key, base_url, model


async def llm_call(prompt: str) -> str:
    """Real OpenAI-compatible chat completion."""
    api_key, base_url, model = _resolve_llm_credentials()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url)
    res = await llm.ainvoke(prompt)
    return res.content


async def embed_call(text: str) -> list[float]:
    """Real OpenAI-compatible embedding, sized to the pgvector column."""
    api_key, base_url, _ = _resolve_llm_credentials()
    model = os.environ.get("EMBEDDING_MODEL") or "text-embedding-3-small"
    url = f"{(base_url or 'https://api.openai.com/v1').rstrip('/')}/embeddings"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "input": text, "dimensions": EMBEDDING_DIM},
        )
        resp.raise_for_status()
        vec = resp.json()["data"][0]["embedding"]
    if len(vec) != EMBEDDING_DIM:
        raise RuntimeError(
            f"Embedding model '{model}' returned {len(vec)} dims; expected {EMBEDDING_DIM}. "
            "Set EMBEDDING_MODEL to a model supporting the 'dimensions' parameter."
        )
    return vec


def get_llm_gateway() -> Callable[[str], Awaitable[str]]:
    return llm_call


def get_embed_gateway() -> Callable[[str], Awaitable[list[float]]]:
    return embed_call
