"""add_farm_diary

Revision ID: 0003_add_farm_diary
Revises: 0002_add_fields
Create Date: 2026-05-02 01:45:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0003_add_farm_diary'
down_revision = '0002_add_fields'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'farm_diary',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('entry_type', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('crop', sa.String(), nullable=True),
        sa.Column('plot', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_farm_diary_id'), 'farm_diary', ['id'], unique=False)
    op.create_index(op.f('ix_farm_diary_user_id'), 'farm_diary', ['user_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_farm_diary_user_id'), table_name='farm_diary')
    op.drop_index(op.f('ix_farm_diary_id'), table_name='farm_diary')
    op.drop_table('farm_diary')
