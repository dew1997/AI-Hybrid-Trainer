"""
Document ingestion into the pgvector knowledge base.
Handles deduplication via content hash and batch embedding.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.rag.chunker import Chunk
from app.rag.embeddings import content_hash, embed_batch

logger = structlog.get_logger(__name__)


async def index_chunks(
    chunks: list[Chunk],
    db: AsyncSession,
    user_id: str | None = None,
    source_type: str = "training_science",
) -> int:
    """
    Embed and store chunks in the documents table.
    Skips chunks whose content_hash already exists for this user/global scope.
    Returns number of new chunks indexed.
    """
    if not chunks:
        return 0

    hashes = [content_hash(c.content) for c in chunks]

    # Find existing hashes to skip (deduplication)
    existing_result = await db.execute(
        select(Document.content_hash).where(Document.content_hash.in_(hashes))
    )
    existing_hashes = {row[0] for row in existing_result.all()}

    new_chunks = [
        (c, h) for c, h in zip(chunks, hashes) if h not in existing_hashes
    ]

    if not new_chunks:
        logger.debug("indexer_all_chunks_exist", count=len(chunks))
        return 0

    texts = [c.content for c, _ in new_chunks]
    embeddings = await embed_batch(texts)

    docs_to_insert = []
    for (chunk, hash_), embedding in zip(new_chunks, embeddings):
        docs_to_insert.append({
            "user_id": user_id,
            "source_type": source_type,
            "title": chunk.metadata.get("title"),
            "content": chunk.content,
            "content_hash": hash_,
            "chunk_index": chunk.chunk_index,
            "metadata": chunk.metadata,
            "embedding": embedding,
            "is_active": True,
        })

    await db.execute(insert(Document).values(docs_to_insert))
    await db.commit()

    logger.info("indexer_chunks_indexed", new=len(docs_to_insert), skipped=len(existing_hashes))
    return len(docs_to_insert)


async def deactivate_user_documents(
    db: AsyncSession,
    user_id: str,
    source_type: str,
) -> None:
    """Mark existing user documents of a given type as inactive before re-indexing."""
    from sqlalchemy import update
    await db.execute(
        update(Document)
        .where(Document.user_id == user_id, Document.source_type == source_type)
        .values(is_active=False)
    )
    await db.commit()
