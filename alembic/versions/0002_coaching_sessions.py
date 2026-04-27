"""Add coaching_sessions and chat_messages tables for persistent conversation history.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-27
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE coaching_sessions (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title       VARCHAR(200) NOT NULL DEFAULT 'New conversation',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX idx_coaching_sessions_user "
        "ON coaching_sessions(user_id, created_at DESC)"
    )

    op.execute("""
        CREATE TABLE chat_messages (
            id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            session_id  UUID NOT NULL REFERENCES coaching_sessions(id) ON DELETE CASCADE,
            role        VARCHAR(20) NOT NULL,
            content     TEXT NOT NULL,
            sources     JSONB NOT NULL DEFAULT '[]',
            actions     JSONB NOT NULL DEFAULT '[]',
            token_usage JSONB,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX idx_chat_messages_session "
        "ON chat_messages(session_id, created_at ASC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_messages")
    op.execute("DROP TABLE IF EXISTS coaching_sessions")
