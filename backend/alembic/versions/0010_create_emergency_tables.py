"""create_emergency_tables

Revision ID: 0010_create_emergency_tables
Revises: 0009_create_marketplace_tables
Create Date: 2026-05-02 12:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0010_create_emergency_tables'
down_revision = '0009_create_marketplace_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'insurance_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('api_endpoint', sa.String(length=500), nullable=True),
        sa.Column('api_key', sa.String(length=500), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'damage_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('farmer_id', sa.String(length=128), nullable=False),
        sa.Column('crop_type', sa.String(length=50), nullable=False),
        sa.Column('growth_stage', sa.String(length=50), nullable=True),
        sa.Column('location_lat', sa.Float(), nullable=False),
        sa.Column('location_lon', sa.Float(), nullable=False),
        sa.Column('location_geom', Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('damage_cause', sa.String(length=100), nullable=False),
        sa.Column('damage_estimate_percent', sa.Float(), nullable=False),
        sa.Column('yield_loss_estimate_percent', sa.Float(), nullable=False),
        sa.Column('number_of_photos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('voice_statement_transcribed', sa.Text(), nullable=True),
        sa.Column('voice_statement_transcribed_en', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='submitted'),
        sa.Column('insurance_provider_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('insurance_providers.id'), nullable=True),
        sa.Column('insurance_claim_id', sa.String(length=128), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('claimed_at', sa.DateTime(), nullable=True),
        sa.Column('pdf_url', sa.String(length=500), nullable=True),
    )
    op.create_index(op.f('ix_damage_reports_status'), 'damage_reports', ['status'], unique=False)
    op.create_index(op.f('ix_damage_reports_location'), 'damage_reports', ['location_lat', 'location_lon'], unique=False)

    op.create_table(
        'report_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('report_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('damage_reports.id'), nullable=False),
        sa.Column('image_data', sa.Text(), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('image_order', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'helpline_call_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('farmer_id', sa.String(length=128), nullable=False),
        sa.Column('location_lat', sa.Float(), nullable=True),
        sa.Column('location_lon', sa.Float(), nullable=True),
        sa.Column('crop_type', sa.String(length=50), nullable=True),
        sa.Column('damage_estimate', sa.Float(), nullable=True),
        sa.Column('call_time', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('call_duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='initiated'),
        sa.Column('operator_notes', sa.Text(), nullable=True),
        sa.Column('follow_up_scheduled', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_helpline_call_logs_status'), 'helpline_call_logs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_helpline_call_logs_status'), table_name='helpline_call_logs')
    op.drop_table('helpline_call_logs')
    op.drop_table('report_images')
    op.drop_index(op.f('ix_damage_reports_location'), table_name='damage_reports')
    op.drop_index(op.f('ix_damage_reports_status'), table_name='damage_reports')
    op.drop_table('damage_reports')
    op.drop_table('insurance_providers')
