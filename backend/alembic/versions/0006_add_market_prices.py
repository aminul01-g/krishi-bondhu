"""add_market_price_table

Revision ID: 0006_add_market_prices
Revises: 0005_add_soil_test
Create Date: 2026-05-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0006_add_market_prices'
down_revision = '0005_add_soil_test'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create market_prices table for historical price tracking
    op.create_table(
        'market_prices',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('crop', sa.String(), nullable=False),
        sa.Column('mandi', sa.String(), nullable=False),
        sa.Column('price_bdt_per_kg', sa.Float(), nullable=False),
        sa.Column('distance_km', sa.Float(), nullable=True),
        sa.Column('prediction_7day', sa.Float(), nullable=True),
        sa.Column('market_trend', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_market_prices_id'), 'market_prices', ['id'], unique=False)
    op.create_index(op.f('ix_market_prices_crop'), 'market_prices', ['crop'], unique=False)
    op.create_index(op.f('ix_market_prices_timestamp'), 'market_prices', ['timestamp'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_market_prices_timestamp'), table_name='market_prices')
    op.drop_index(op.f('ix_market_prices_crop'), table_name='market_prices')
    op.drop_index(op.f('ix_market_prices_id'), table_name='market_prices')
    op.drop_table('market_prices')
