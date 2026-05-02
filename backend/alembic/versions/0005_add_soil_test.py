"""add_soil_test

Revision ID: 0005_add_soil_test
Revises: 0004_add_tips
Create Date: 2026-05-01 20:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import json

# revision identifiers, used by Alembic.
revision = '0005_add_soil_test'
down_revision = '0004_add_tips'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # We use SQLite compatible types for the local dev setup
    op.create_table(
        'soil_test_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('crop', sa.String(), nullable=True),
        sa.Column('image_url', sa.String(), nullable=True),
        sa.Column('diy_inputs', sa.JSON(), nullable=True),
        sa.Column('derived_texture', sa.String(), nullable=True),
        sa.Column('derived_ph', sa.Float(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_soil_test_logs_id'), 'soil_test_logs', ['id'], unique=False)
    op.create_index(op.f('ix_soil_test_logs_user_id'), 'soil_test_logs', ['user_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_soil_test_logs_user_id'), table_name='soil_test_logs')
    op.drop_index(op.f('ix_soil_test_logs_id'), table_name='soil_test_logs')
    op.drop_table('soil_test_logs')
