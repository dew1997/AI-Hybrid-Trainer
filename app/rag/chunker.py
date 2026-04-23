"""
Text chunking strategies for different document types.
"""

from dataclasses import dataclass

import tiktoken

ENCODING = tiktoken.get_encoding("cl100k_base")
CHUNK_SIZE_TOKENS = 600
CHUNK_OVERLAP_TOKENS = 100


@dataclass
class Chunk:
    content: str
    chunk_index: int
    metadata: dict


def count_tokens(text: str) -> int:
    return len(ENCODING.encode(text))


def chunk_training_article(
    content: str,
    title: str,
    metadata: dict | None = None,
) -> list[Chunk]:
    """
    Recursive paragraph → sentence splitting for training science articles.
    Target: 600 tokens per chunk, 100 token overlap.
    """
    base_meta = {"title": title, "source_type": "training_science", **(metadata or {})}
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    chunks: list[Chunk] = []
    current_tokens = 0
    current_parts: list[str] = []

    def flush(overlap_parts: list[str]) -> list[str]:
        if current_parts:
            text = "\n\n".join(current_parts)
            chunks.append(Chunk(
                content=text,
                chunk_index=len(chunks),
                metadata={**base_meta, "chunk_index": len(chunks)},
            ))
        # Return last ~CHUNK_OVERLAP_TOKENS tokens worth of parts for overlap
        overlap: list[str] = []
        overlap_tokens = 0
        for part in reversed(overlap_parts):
            t = count_tokens(part)
            if overlap_tokens + t > CHUNK_OVERLAP_TOKENS:
                break
            overlap.insert(0, part)
            overlap_tokens += t
        return overlap

    for para in paragraphs:
        para_tokens = count_tokens(para)
        if current_tokens + para_tokens > CHUNK_SIZE_TOKENS and current_parts:
            overlap = flush(current_parts)
            current_parts = overlap[:]
            current_tokens = sum(count_tokens(p) for p in current_parts)

        current_parts.append(para)
        current_tokens += para_tokens

    if current_parts:
        flush(current_parts)

    return chunks


def chunk_workout_history(
    workouts_summary: str,
    user_id: str,
    week_range_start: str,
    week_range_end: str,
) -> list[Chunk]:
    """Single chunk per 2-week workout narrative summary."""
    return [
        Chunk(
            content=workouts_summary,
            chunk_index=0,
            metadata={
                "source_type": "workout_history",
                "user_id": user_id,
                "week_range_start": week_range_start,
                "week_range_end": week_range_end,
            },
        )
    ]


def chunk_user_profile(profile_text: str, user_id: str) -> list[Chunk]:
    """User profile is always a single chunk."""
    return [
        Chunk(
            content=profile_text,
            chunk_index=0,
            metadata={"source_type": "user_profile", "user_id": user_id},
        )
    ]
