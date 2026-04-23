import hashlib

import structlog
from openai import AsyncOpenAI

from app.config import settings

logger = structlog.get_logger(__name__)
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed(text: str) -> list[float]:
    """Embed a single string. Returns a 1536-dim vector."""
    client = _get_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text.strip(),
    )
    return response.data[0].embedding


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple strings in one API call (max 2048 inputs per call)."""
    if not texts:
        return []
    client = _get_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=[t.strip() for t in texts],
    )
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


def content_hash(text: str) -> str:
    """SHA-256 hash of content for deduplication."""
    return hashlib.sha256(text.encode()).hexdigest()
