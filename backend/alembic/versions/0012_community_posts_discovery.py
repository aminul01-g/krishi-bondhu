"""community posts discovery (district, ai_answer, counts, question_upvotes)

Revision ID: 0012_community_posts_discovery
Revises: 0011_create_sqlite_fallback_tables
Create Date: 2026-06-27 12:00:00.000000

Adds district + AI-answer + denormalized count columns to community_questions,
and a new question_upvotes table (toggle upvotes on posts).

Chains off 0011 (the SQLite fallback migration) which is the current head:
    ... 0010_create_emergency_tables
        -> 56bd0a562c28_add_username_and_password_to_users
        -> 0011_create_sqlite_fallback_tables
        -> 0012_community_posts_discovery   (this one)

Idempotent: uses existence checks so it is safe to re-run on Postgres (where
0008 created the base table) and on SQLite (where 0011 created it).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision = '0012_community_posts_discovery'
down_revision = '0011_create_sqlite_fallback_tables'
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    return table_name in sa_inspect(bind).get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    return column_name in [c["name"] for c in sa_inspect(bind).get_columns(table_name)]


def _index_exists(index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    for table in inspector.get_table_names():
        if index_name in [i["name"] for i in inspector.get_indexes(table)]:
            return True
    return False


def upgrade() -> None:
    # New columns on community_questions. All are nullable / have defaults so the
    # ALTER TABLE is cheap and safe on both Postgres and SQLite.
    if _table_exists("community_questions"):
        if not _column_exists("community_questions", "district"):
            op.add_column(
                "community_questions",
                sa.Column("district", sa.String(length=100), nullable=True),
            )
        if not _column_exists("community_questions", "ai_answer"):
            op.add_column(
                "community_questions",
                sa.Column("ai_answer", sa.Text(), nullable=True),
            )
        if not _column_exists("community_questions", "ai_answer_generated_at"):
            op.add_column(
                "community_questions",
                sa.Column("ai_answer_generated_at", sa.DateTime(), nullable=True),
            )
        if not _column_exists("community_questions", "upvotes_count"):
            op.add_column(
                "community_questions",
                sa.Column("upvotes_count", sa.Integer(), nullable=False, server_default="0"),
            )
        if not _column_exists("community_questions", "answers_count"):
            op.add_column(
                "community_questions",
                sa.Column("answers_count", sa.Integer(), nullable=False, server_default="0"),
            )

    # New question_upvotes table (toggle upvotes on posts).
    if not _table_exists("question_upvotes"):
        op.create_table(
            "question_upvotes",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column(
                "question_id",
                sa.String(length=36),
                sa.ForeignKey("community_questions.id"),
                nullable=False,
            ),
            sa.Column("farmer_id_hashed", sa.String(length=128), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
        op.create_index(
            "ix_question_upvotes_question_id",
            "question_upvotes",
            ["question_id"],
            unique=False,
        )
        op.create_index(
            "idx_question_upvotes_unique",
            "question_upvotes",
            ["question_id", "farmer_id_hashed"],
            unique=True,
        )


def downgrade() -> None:
    try:
        op.drop_index("idx_question_upvotes_unique", table_name="question_upvotes")
    except Exception:
        pass
    try:
        op.drop_index("ix_question_upvotes_question_id", table_name="question_upvotes")
    except Exception:
        pass
    if _table_exists("question_upvotes"):
        op.drop_table("question_upvotes")

    for col in ("answers_count", "upvotes_count", "ai_answer_generated_at", "ai_answer", "district"):
        if _table_exists("community_questions") and _column_exists("community_questions", col):
            try:
                op.drop_column("community_questions", col)
            except Exception:
                pass
