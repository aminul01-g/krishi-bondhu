"""add_fields_to_conversations

Revision ID: 0002_add_fields
Revises: 0001_initial
Create Date: 2025-11-08 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002_add_fields'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade():
    # Only add fields that don't already exist
    # transcript already exists in 0001_initial, so we skip it here
    op.add_column('conversations', sa.Column('media_url', sa.String(), nullable=True))
    op.add_column('conversations', sa.Column('confidence', sa.Float(), nullable=True))

def downgrade():
    op.drop_column('conversations', 'media_url')
    op.drop_column('conversations', 'confidence')
