"""create_postgis_pgvector_extensions

Revision ID: 0007_create_postgis_pgvector_extensions
Revises: 0006_add_market_prices
Create Date: 2026-05-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0007_create_postgis_pgvector_extensions'
down_revision = '0006_add_market_prices'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgvector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pgvector")
    op.execute("DROP EXTENSION IF EXISTS postgis")
