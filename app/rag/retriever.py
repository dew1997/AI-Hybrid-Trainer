"""
Hybrid RAG retrieval: semantic (pgvector cosine) + keyword (pg_trgm trigram)
combined via Reciprocal Rank Fusion (RRF).
"""

from dataclasses import dataclass

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.embeddings import embed

logger = structlog.get_logger(__name__)


@dataclass
class RetrievedChunk:
    id: str
    content: str
    title: str | None
    source_type: str
    metadata: dict
    semantic_score: float
    keyword_score: float
    rrf_score: float


async def hybrid_search(
    query: str,
    db: AsyncSession,
    user_id: str | None = None,
    top_k: int = 6,
    alpha: float = 0.7,
    source_filter: str | None = None,
) -> list[RetrievedChunk]:
    """
    Retrieve top_k most relevant chunks via hybrid search.

    alpha: weight for semantic score (1-alpha for keyword)
    source_filter: 'training_science' | 'workout_history' | 'user_profile' | None (all)
    """
    query_embedding = await embed(query)
    candidate_k = top_k * 3

    # Format embedding as pgvector literal string for raw SQL
    embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

    source_clause = ""
    params: dict = {
        "embedding": embedding_str,
        "user_id": user_id,
        "candidate_k": candidate_k,
        "query": query,
    }

    if source_filter:
        source_clause = "AND source_type = :source_filter"
        params["source_filter"] = source_filter

    user_clause = "(user_id = :user_id OR user_id IS NULL)" if user_id else "user_id IS NULL"

    # Semantic search
    semantic_sql = text(f"""
        SELECT
            id::text,
            content,
            title,
            source_type,
            metadata,
            1 - (embedding <=> CAST(:embedding AS vector)) AS semantic_score
        FROM documents
        WHERE is_active = TRUE
          AND {user_clause}
          {source_clause}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :candidate_k
    """)

    # Keyword search via trigram similarity
    keyword_sql = text(f"""
        SELECT
            id::text,
            content,
            title,
            source_type,
            metadata,
            similarity(content, :query) AS keyword_score
        FROM documents
        WHERE is_active = TRUE
          AND {user_clause}
          {source_clause}
          AND content % :query
        ORDER BY similarity(content, :query) DESC
        LIMIT :candidate_k
    """)

    semantic_rows = (await db.execute(semantic_sql, params)).mappings().all()
    keyword_rows = (await db.execute(keyword_sql, params)).mappings().all()

    merged = _reciprocal_rank_fusion(
        semantic_rows=list(semantic_rows),
        keyword_rows=list(keyword_rows),
        alpha=alpha,
        top_k=top_k,
    )

    logger.debug(
        "rag_retrieval",
        query_preview=query[:60],
        semantic_candidates=len(semantic_rows),
        keyword_candidates=len(keyword_rows),
        returned=len(merged),
    )

    return merged


def _reciprocal_rank_fusion(
    semantic_rows: list,
    keyword_rows: list,
    alpha: float,
    top_k: int,
    k: int = 60,
) -> list[RetrievedChunk]:
    """
    RRF score = alpha * (1/(k+rank_semantic)) + (1-alpha) * (1/(k+rank_keyword))
    Documents not present in one list get rank = len(list) + 1 (lowest score).
    """
    semantic_rank = {row["id"]: i + 1 for i, row in enumerate(semantic_rows)}
    keyword_rank = {row["id"]: i + 1 for i, row in enumerate(keyword_rows)}
    all_scores_map = {
        row["id"]: {
            "content": row["content"],
            "title": row.get("title"),
            "source_type": row["source_type"],
            "metadata": row.get("metadata") or {},
            "semantic_score": float(row.get("semantic_score", 0)),
            "keyword_score": 0.0,
        }
        for row in semantic_rows
    }
    for row in keyword_rows:
        doc_id = row["id"]
        if doc_id not in all_scores_map:
            all_scores_map[doc_id] = {
                "content": row["content"],
                "title": row.get("title"),
                "source_type": row["source_type"],
                "metadata": row.get("metadata") or {},
                "semantic_score": 0.0,
                "keyword_score": float(row.get("keyword_score", 0)),
            }
        else:
            all_scores_map[doc_id]["keyword_score"] = float(row.get("keyword_score", 0))

    max_sem_rank = len(semantic_rows) + 1
    max_key_rank = len(keyword_rows) + 1

    scored: list[tuple[str, float]] = []
    for doc_id, data in all_scores_map.items():
        sem_r = semantic_rank.get(doc_id, max_sem_rank)
        key_r = keyword_rank.get(doc_id, max_key_rank)
        rrf = alpha * (1 / (k + sem_r)) + (1 - alpha) * (1 / (k + key_r))
        scored.append((doc_id, rrf))

    scored.sort(key=lambda x: x[1], reverse=True)

    results = []
    for doc_id, rrf_score in scored[:top_k]:
        data = all_scores_map[doc_id]
        results.append(
            RetrievedChunk(
                id=doc_id,
                content=data["content"],
                title=data["title"],
                source_type=data["source_type"],
                metadata=data["metadata"],
                semantic_score=data["semantic_score"],
                keyword_score=data["keyword_score"],
                rrf_score=round(rrf_score, 6),
            )
        )
    return results


def build_rag_context(chunks: list[RetrievedChunk], max_tokens: int = 2400) -> str:
    """
    Assemble retrieved chunks into a context string within a token budget.
    Higher-ranked chunks are included first; lower-ranked dropped if over budget.
    """
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")

    lines: list[str] = []
    used_tokens = 0

    for chunk in chunks:
        header = f"[{chunk.source_type.upper()}] {chunk.title or 'Reference'}"
        block = f"{header}\n{chunk.content}\n"
        tokens = len(enc.encode(block))

        if used_tokens + tokens > max_tokens:
            break

        lines.append(block)
        used_tokens += tokens

    return "\n---\n".join(lines)
