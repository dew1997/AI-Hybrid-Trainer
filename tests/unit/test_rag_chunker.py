
from app.rag.chunker import (
    CHUNK_SIZE_TOKENS,
    chunk_training_article,
    chunk_user_profile,
    chunk_workout_history,
    count_tokens,
)


class TestChunkTrainingArticle:
    def test_short_article_produces_single_chunk(self):
        content = "This is a short training article.\n\nIt has two paragraphs."
        chunks = chunk_training_article(content, title="Test Article")
        assert len(chunks) == 1
        assert chunks[0].chunk_index == 0

    def test_long_article_produces_multiple_chunks(self):
        # Create content that exceeds chunk size
        paragraph = "This is a paragraph about training principles. " * 20
        content = "\n\n".join([paragraph] * 10)
        chunks = chunk_training_article(content, title="Long Article")
        assert len(chunks) > 1

    def test_each_chunk_within_token_limit(self):
        paragraph = "Training science paragraph about periodization and recovery. " * 15
        content = "\n\n".join([paragraph] * 8)
        chunks = chunk_training_article(content, title="Article")
        for chunk in chunks:
            assert count_tokens(chunk.content) <= CHUNK_SIZE_TOKENS * 1.2  # small buffer

    def test_metadata_contains_title(self):
        chunks = chunk_training_article("Short content.", title="My Title")
        assert chunks[0].metadata["title"] == "My Title"

    def test_metadata_contains_source_type(self):
        chunks = chunk_training_article("Content.", title="T")
        assert chunks[0].metadata["source_type"] == "training_science"

    def test_extra_metadata_is_passed_through(self):
        chunks = chunk_training_article(
            "Content.", title="T", metadata={"topic": "recovery"}
        )
        assert chunks[0].metadata["topic"] == "recovery"


class TestChunkWorkoutHistory:
    def test_returns_single_chunk(self):
        chunks = chunk_workout_history(
            "Week 1: 3 runs, 2 gym sessions.",
            user_id="user-123",
            week_range_start="2024-03-01",
            week_range_end="2024-03-14",
        )
        assert len(chunks) == 1

    def test_metadata_contains_user_id(self):
        chunks = chunk_workout_history("Summary", "user-abc", "2024-01-01", "2024-01-14")
        assert chunks[0].metadata["user_id"] == "user-abc"

    def test_chunk_index_is_zero(self):
        chunks = chunk_workout_history("Summary", "user-abc", "2024-01-01", "2024-01-14")
        assert chunks[0].chunk_index == 0


class TestChunkUserProfile:
    def test_returns_single_chunk(self):
        chunks = chunk_user_profile("Name: Athlete. Goal: Marathon.", user_id="user-1")
        assert len(chunks) == 1

    def test_content_preserved(self):
        content = "Name: Athlete. Goal: Marathon."
        chunks = chunk_user_profile(content, user_id="user-1")
        assert chunks[0].content == content
