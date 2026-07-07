"""add tables missing from the migration history

Eight model tables were only ever created by ``Base.metadata.create_all`` and had
no migration: async_tasks, farmer_profiles, finance_schemes, insurance_quotes,
irrigation_logs, knowledge_facts, marketplace_listings, listing_contact_logs.
This closed the gap so Alembic can be the single schema authority on PostgreSQL
(see main.py startup / AUTO_CREATE_TABLES).

Each table is guarded with an existence check so this migration is idempotent and
safe on databases where create_all already created them. Column types mirror the
SQLAlchemy models exactly (no server defaults for Python-side ``default=`` values)
so create_all'd and Alembic'd schemas match.

Like 0009, this migration is a no-op on SQLite, where the app relies on
create_all (the Postgres/PostGIS/pgvector column types cannot all replay there).

Revision ID: 0014_add_missing_tables
Revises: 0013_index_conversation_user_id
Create Date: 2026-07-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID, JSON as PG_JSON


revision = '0014_add_missing_tables'
down_revision = '0013_index_conversation_user_id'
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    try:
        return name in inspect(bind).get_table_names()
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    # SQLite bootstraps these via create_all (consistent with 0009).
    if bind.dialect.name == "sqlite":
        return

    if not _has_table(bind, "async_tasks"):
        op.create_table(
            "async_tasks",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("task_type", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True),
            sa.Column("result", PG_JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )
        op.create_index(op.f("ix_async_tasks_id"), "async_tasks", ["id"], unique=False)
        op.create_index(op.f("ix_async_tasks_user_id"), "async_tasks", ["user_id"], unique=False)

    if not _has_table(bind, "farmer_profiles"):
        op.create_table(
            "farmer_profiles",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("district", sa.String(), nullable=True),
            sa.Column("upazila", sa.String(), nullable=True),
            sa.Column("crops", PG_JSON(), nullable=True),
            sa.Column("land_area_bigha", sa.Float(), nullable=True),
            sa.Column("farming_experience_years", sa.Integer(), nullable=True),
            sa.Column("phone_number", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )
        op.create_index(op.f("ix_farmer_profiles_id"), "farmer_profiles", ["id"], unique=False)
        # user_id is unique in the model — the upsert-by-user logic depends on it.
        op.create_index(op.f("ix_farmer_profiles_user_id"), "farmer_profiles", ["user_id"], unique=True)

    if not _has_table(bind, "finance_schemes"):
        op.create_table(
            "finance_schemes",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("name_bn", sa.String(), nullable=False),
            sa.Column("name_en", sa.String(), nullable=True),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("eligibility_criteria", PG_JSON(), nullable=True),
            sa.Column("description_bn", sa.Text(), nullable=True),
            sa.Column("how_to_apply_bn", sa.Text(), nullable=True),
            sa.Column("apply_link", sa.String(), nullable=True),
        )
        op.create_index(op.f("ix_finance_schemes_id"), "finance_schemes", ["id"], unique=False)

    if not _has_table(bind, "insurance_quotes"):
        op.create_table(
            "insurance_quotes",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("crop", sa.String(), nullable=False),
            sa.Column("land_size", sa.Float(), nullable=True),
            sa.Column("premium_estimate", sa.Float(), nullable=True),
            sa.Column("payout_triggers", sa.Text(), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )
        op.create_index(op.f("ix_insurance_quotes_id"), "insurance_quotes", ["id"], unique=False)
        op.create_index(op.f("ix_insurance_quotes_user_id"), "insurance_quotes", ["user_id"], unique=False)

    if not _has_table(bind, "irrigation_logs"):
        op.create_table(
            "irrigation_logs",
            sa.Column("id", sa.String(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.Column("soil_moisture_index", sa.Float(), nullable=True),
            sa.Column("advice", sa.Text(), nullable=True),
            sa.Column("action_taken", sa.Integer(), nullable=True),
        )
        op.create_index(op.f("ix_irrigation_logs_id"), "irrigation_logs", ["id"], unique=False)
        op.create_index(op.f("ix_irrigation_logs_user_id"), "irrigation_logs", ["user_id"], unique=False)

    if not _has_table(bind, "knowledge_facts"):
        op.create_table(
            "knowledge_facts",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("fact_key", sa.String(), nullable=True),
            sa.Column("fact_value", sa.Text(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("source_conv_id", sa.Integer(), nullable=True),
            sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        )
        op.create_index(op.f("ix_knowledge_facts_id"), "knowledge_facts", ["id"], unique=False)
        op.create_index(op.f("ix_knowledge_facts_user_id"), "knowledge_facts", ["user_id"], unique=False)
        op.create_index(op.f("ix_knowledge_facts_fact_key"), "knowledge_facts", ["fact_key"], unique=False)

    if not _has_table(bind, "marketplace_listings"):
        op.create_table(
            "marketplace_listings",
            sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("seller_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("seller_name", sa.String(length=200), nullable=False),
            sa.Column("seller_phone", sa.String(length=20), nullable=True),
            sa.Column("crop", sa.String(length=100), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("quantity_kg", sa.Integer(), nullable=False),
            sa.Column("price_per_kg", sa.Float(), nullable=False),
            sa.Column("district", sa.String(length=100), nullable=True),
            sa.Column("upazila", sa.String(length=100), nullable=True),
            sa.Column("photo_url", sa.String(length=500), nullable=True),
            sa.Column("listing_type", sa.String(length=20), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("posted_date", sa.DateTime(), nullable=True),
        )
        op.create_index(op.f("ix_marketplace_listings_seller_id"), "marketplace_listings", ["seller_id"], unique=False)
        op.create_index(op.f("ix_marketplace_listings_crop"), "marketplace_listings", ["crop"], unique=False)
        op.create_index(op.f("ix_marketplace_listings_district"), "marketplace_listings", ["district"], unique=False)
        op.create_index(op.f("ix_marketplace_listings_listing_type"), "marketplace_listings", ["listing_type"], unique=False)
        op.create_index(op.f("ix_marketplace_listings_is_active"), "marketplace_listings", ["is_active"], unique=False)
        op.create_index(op.f("ix_marketplace_listings_posted_date"), "marketplace_listings", ["posted_date"], unique=False)
        op.create_index("idx_listings_crop_district", "marketplace_listings", ["crop", "district"], unique=False)
        op.create_index("idx_listings_active_posted", "marketplace_listings", ["is_active", "posted_date"], unique=False)

    if not _has_table(bind, "listing_contact_logs"):
        op.create_table(
            "listing_contact_logs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("listing_id", UUID(as_uuid=True), sa.ForeignKey("marketplace_listings.id"), nullable=False),
            sa.Column("buyer_id", sa.Integer(), nullable=True),
            sa.Column("contacted_at", sa.DateTime(), nullable=True),
        )
        op.create_index(op.f("ix_listing_contact_logs_id"), "listing_contact_logs", ["id"], unique=False)
        op.create_index(op.f("ix_listing_contact_logs_listing_id"), "listing_contact_logs", ["listing_id"], unique=False)
        op.create_index(op.f("ix_listing_contact_logs_contacted_at"), "listing_contact_logs", ["contacted_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    for table in (
        "listing_contact_logs",
        "marketplace_listings",
        "knowledge_facts",
        "irrigation_logs",
        "insurance_quotes",
        "finance_schemes",
        "farmer_profiles",
        "async_tasks",
    ):
        if _has_table(bind, table):
            op.drop_table(table)
