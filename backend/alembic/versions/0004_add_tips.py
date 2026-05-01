"""add_tips

Revision ID: 0004_add_tips
Revises: 0003_add_farm_diary
Create Date: 2026-05-02 01:55:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0004_add_tips'
down_revision = '0003_add_farm_diary'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'curated_tips',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('crop', sa.String(), nullable=False),
        sa.Column('growth_stage_days_start', sa.Integer(), nullable=False),
        sa.Column('growth_stage_days_end', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('tip_text_bn', sa.Text(), nullable=False),
        sa.Column('audio_url', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_curated_tips_id'), 'curated_tips', ['id'], unique=False)
    op.create_index(op.f('ix_curated_tips_crop'), 'curated_tips', ['crop'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_curated_tips_crop'), table_name='curated_tips')
    op.drop_index(op.f('ix_curated_tips_id'), table_name='curated_tips')
    op.drop_table('curated_tips')
