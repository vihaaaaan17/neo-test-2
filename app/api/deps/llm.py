import logging
import os
from typing import Callable, Awaitable

import httpx

from app.core.config import resolve_llm_provider

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768  # must match document_blocks.embedding Vector(768)


async def llm_call(prompt: str) -> str:
    """Real OpenAI-compatible chat completion."""
    provider = resolve_llm_provider(require_key=True)
    api_key, base_url, model = provider.api_key, provider.base_url, provider.model
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url)
    res = await llm.ainvoke(prompt)
    return res.content


async def embed_call(text: str) -> list[float]:
    """Real OpenAI-compatible embedding, sized to the pgvector column."""
    provider = resolve_llm_provider(require_key=True)
    api_key, base_url = provider.api_key, provider.base_url
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
