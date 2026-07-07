"""index conversations.user_id

Conversation history is filtered by ``user_id`` on every chat / chat-stream
request. The column previously had no index, forcing a sequential scan that
degrades as the table grows. This migration adds it.

Revision ID: 0013_index_conversation_user_id
Revises: 0012_community_posts_discovery
Create Date: 2026-07-07 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '0013_index_conversation_user_id'
down_revision = '0012_community_posts_discovery'
branch_labels = None
depends_on = None

INDEX_NAME = 'ix_conversations_user_id'
TABLE_NAME = 'conversations'


def _index_exists(bind, table_name: str, index_name: str) -> bool:
    """Return True if an index of that name already exists on the table.

    Guards against environments where the table was created via
    ``Base.metadata.create_all`` (which already emits the model's index=True),
    so re-running the migration is idempotent and won't error.
    """
    try:
        inspector = inspect(bind)
        if table_name not in inspector.get_table_names():
            return True  # table absent -> nothing to do; treat as "handled"
        existing = {ix['name'] for ix in inspector.get_indexes(table_name)}
        return index_name in existing
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    if not _index_exists(bind, TABLE_NAME, INDEX_NAME):
        op.create_index(
            op.f(INDEX_NAME), TABLE_NAME, ['user_id'], unique=False
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _index_exists(bind, TABLE_NAME, INDEX_NAME):
        op.drop_index(op.f(INDEX_NAME), table_name=TABLE_NAME)
