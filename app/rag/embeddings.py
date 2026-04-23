"""
Local embedding using sentence-transformers (all-MiniLM-L6-v2, 384-dim).
No API key required — model is downloaded on first use and cached locally.
"""

import hashlib

import structlog
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = structlog.get_logger(__name__)
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("loading_embedding_model", model=settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
    return _model


async def embed(text: str) -> list[float]:
    """Embed a single string. Returns a 384-dim vector."""
    model = _get_model()
    vector = model.encode(text.strip(), normalize_embeddings=True)
    return vector.tolist()


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple strings in one pass (CPU/GPU batched)."""
    if not texts:
        return []
    model = _get_model()
    vectors = model.encode([t.strip() for t in texts], normalize_embeddings=True, batch_size=32)
    return [v.tolist() for v in vectors]


def content_hash(text: str) -> str:
    """SHA-256 hash of content for deduplication."""
    return hashlib.sha256(text.encode()).hexdigest()
