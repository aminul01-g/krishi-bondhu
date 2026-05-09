"""create_sqlite_fallback_tables

Revision ID: 0011_create_sqlite_fallback_tables
Revises: 0010_create_emergency_tables
Create Date: 2026-05-09 12:00:00.000000

Creates all marketplace, community, emergency, and production tables
using SQLite-compatible column types when running on SQLite.

Migrations 0008-0010 skip SQLite entirely (`if dialect == 'sqlite': return`),
which means the tables are never created on SQLite.  This migration fills
that gap by using plain column types (no Geometry, no Vector, no UUID).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

# revision identifiers, used by Alembic.
revision = '0011_create_sqlite_fallback_tables'
down_revision = '56bd0a562c28'
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    """Check if a table already exists in the database."""
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # This migration is only for SQLite.  On PostgreSQL the tables were
    # already created by migrations 0008–0010.
    if op.get_context().dialect.name != "sqlite":
        return

    # ── Community Q&A tables ──────────────────────────────────────────────

    if not _table_exists("community_questions"):
        op.create_table(
            'community_questions',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('farmer_id_hashed', sa.String(128), nullable=False),
            sa.Column('question_text', sa.Text(), nullable=False),
            sa.Column('question_text_en', sa.Text(), nullable=True),
            sa.Column('crop_type', sa.String(50), nullable=False),
            sa.Column('growth_stage', sa.String(50), nullable=True),
            sa.Column('photo_url', sa.String(500), nullable=True),
            sa.Column('lat', sa.Float(), nullable=False),
            sa.Column('lon', sa.Float(), nullable=False),
            # Geometry and Vector columns omitted for SQLite
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('moderation_flag', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('admin_review_needed', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    if not _table_exists("agricultural_experts"):
        op.create_table(
            'agricultural_experts',
            sa.Column('id', sa.String(128), primary_key=True, nullable=False),
            # region_geom omitted for SQLite
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('phone_number', sa.String(20), nullable=False),
            sa.Column('email', sa.String(100), nullable=True),
            sa.Column('region', sa.String(100), nullable=False),
            sa.Column('credentials', sa.String(255), nullable=True),
            sa.Column('areas_of_expertise', sa.JSON(), nullable=True),
            sa.Column('response_time_avg_hours', sa.Float(), nullable=True),
            sa.Column('total_answers', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('rating_avg', sa.Float(), nullable=False, server_default='4.0'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('last_active_at', sa.DateTime(), nullable=True),
        )

    if not _table_exists("community_answers"):
        op.create_table(
            'community_answers',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('question_id', sa.String(36), sa.ForeignKey('community_questions.id'), nullable=False),
            sa.Column('answerer_id', sa.String(128), nullable=False),
            sa.Column('answerer_name', sa.String(100), nullable=False),
            sa.Column('answerer_credentials', sa.String(255), nullable=True),
            sa.Column('answer_text', sa.Text(), nullable=False),
            sa.Column('answer_text_en', sa.Text(), nullable=True),
            sa.Column('is_expert_answer', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('verified_at', sa.DateTime(), nullable=True),
        )

    if not _table_exists("answer_upvotes"):
        op.create_table(
            'answer_upvotes',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('answer_id', sa.String(36), sa.ForeignKey('community_answers.id'), nullable=False),
            sa.Column('farmer_id_hashed', sa.String(128), nullable=False),
            sa.Column('rating', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists("escalation_queue"):
        op.create_table(
            'escalation_queue',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('question_id', sa.String(36), sa.ForeignKey('community_questions.id'), nullable=False, unique=True),
            sa.Column('expert_id', sa.String(128), sa.ForeignKey('agricultural_experts.id'), nullable=True),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('auto_escalate_at', sa.DateTime(), nullable=True),
            sa.Column('assigned_at', sa.DateTime(), nullable=True),
            sa.Column('resolved_at', sa.DateTime(), nullable=True),
        )

    # ── Marketplace tables ────────────────────────────────────────────────

    if not _table_exists("dealers"):
        op.create_table(
            'dealers',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('phone_number', sa.String(20), nullable=False),
            sa.Column('email', sa.String(100), nullable=True),
            sa.Column('location_lat', sa.Float(), nullable=False),
            sa.Column('location_lon', sa.Float(), nullable=False),
            # location_geom omitted for SQLite
            sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('verification_status', sa.String(50), nullable=False, server_default='pending'),
            sa.Column('verified_at', sa.DateTime(), nullable=True),
            sa.Column('verified_by', sa.String(128), nullable=True),
            sa.Column('regions_served', sa.JSON(), nullable=True),
            sa.Column('registration_date', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('last_updated', sa.DateTime(), nullable=True),
        )

    if not _table_exists("dealer_inventory"):
        op.create_table(
            'dealer_inventory',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('dealer_id', sa.String(36), sa.ForeignKey('dealers.id'), nullable=False),
            sa.Column('product_name', sa.String(200), nullable=False),
            sa.Column('input_type', sa.String(50), nullable=False),
            sa.Column('crop_type', sa.String(50), nullable=True),
            sa.Column('batch_number', sa.String(100), nullable=True),
            sa.Column('manufacturer', sa.String(200), nullable=True),
            sa.Column('quantity_in_stock', sa.Integer(), nullable=False),
            sa.Column('price_bdt', sa.Float(), nullable=False),
            sa.Column('expiry_date', sa.Date(), nullable=False),
            sa.Column('added_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('last_updated', sa.DateTime(), nullable=True),
        )

    if not _table_exists("verified_products"):
        op.create_table(
            'verified_products',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('barcode', sa.String(50), nullable=False),
            sa.Column('qr_code', sa.String(500), nullable=True),
            sa.Column('product_name', sa.String(200), nullable=False),
            sa.Column('manufacturer', sa.String(200), nullable=False),
            sa.Column('batch_number', sa.String(100), nullable=False),
            sa.Column('active_ingredient', sa.Text(), nullable=True),
            sa.Column('npk_ratio', sa.String(20), nullable=True),
            sa.Column('dose_per_application', sa.String(100), nullable=True),
            sa.Column('registered_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('expiry_date', sa.Date(), nullable=False),
            sa.Column('government_registry', sa.String(50), nullable=True),
            sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('verification_source', sa.String(50), nullable=False, server_default='local_db'),
        )

    if not _table_exists("product_scans"):
        op.create_table(
            'product_scans',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('farmer_id_hashed', sa.String(128), nullable=False),
            sa.Column('barcode', sa.String(50), nullable=True),
            sa.Column('qr_text', sa.String(500), nullable=True),
            sa.Column('verified_product_id', sa.String(36), sa.ForeignKey('verified_products.id'), nullable=True),
            sa.Column('verification_result', sa.String(50), nullable=False),
            sa.Column('confidence_score', sa.Float(), nullable=True),
            sa.Column('scanned_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('location_lat', sa.Float(), nullable=True),
            sa.Column('location_lon', sa.Float(), nullable=True),
        )

    # ── Emergency tables ──────────────────────────────────────────────────

    if not _table_exists("insurance_providers"):
        op.create_table(
            'insurance_providers',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('email', sa.String(100), nullable=True),
            sa.Column('phone_number', sa.String(20), nullable=True),
            sa.Column('api_endpoint', sa.String(500), nullable=True),
            sa.Column('api_key', sa.String(500), nullable=True),
            sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists("damage_reports"):
        op.create_table(
            'damage_reports',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('farmer_id', sa.String(128), nullable=False),
            sa.Column('crop_type', sa.String(50), nullable=False),
            sa.Column('growth_stage', sa.String(50), nullable=True),
            sa.Column('location_lat', sa.Float(), nullable=False),
            sa.Column('location_lon', sa.Float(), nullable=False),
            # location_geom omitted for SQLite
            sa.Column('damage_cause', sa.String(100), nullable=False),
            sa.Column('damage_estimate_percent', sa.Float(), nullable=False),
            sa.Column('yield_loss_estimate_percent', sa.Float(), nullable=False),
            sa.Column('number_of_photos', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('voice_statement_transcribed', sa.Text(), nullable=True),
            sa.Column('voice_statement_transcribed_en', sa.Text(), nullable=True),
            sa.Column('status', sa.String(50), nullable=False, server_default='submitted'),
            sa.Column('insurance_provider_id', sa.String(36), sa.ForeignKey('insurance_providers.id'), nullable=True),
            sa.Column('insurance_claim_id', sa.String(128), nullable=True),
            sa.Column('submitted_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('reviewed_at', sa.DateTime(), nullable=True),
            sa.Column('approved_at', sa.DateTime(), nullable=True),
            sa.Column('claimed_at', sa.DateTime(), nullable=True),
            sa.Column('pdf_url', sa.String(500), nullable=True),
        )

    if not _table_exists("report_images"):
        op.create_table(
            'report_images',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('report_id', sa.String(36), sa.ForeignKey('damage_reports.id'), nullable=False),
            sa.Column('image_data', sa.Text(), nullable=True),
            sa.Column('image_url', sa.String(500), nullable=True),
            sa.Column('image_order', sa.Integer(), nullable=True),
            sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not _table_exists("helpline_call_logs"):
        op.create_table(
            'helpline_call_logs',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('farmer_id', sa.String(128), nullable=False),
            sa.Column('location_lat', sa.Float(), nullable=True),
            sa.Column('location_lon', sa.Float(), nullable=True),
            sa.Column('crop_type', sa.String(50), nullable=True),
            sa.Column('damage_estimate', sa.Float(), nullable=True),
            sa.Column('call_time', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('call_duration_seconds', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(50), nullable=False, server_default='initiated'),
            sa.Column('operator_notes', sa.Text(), nullable=True),
            sa.Column('follow_up_scheduled', sa.DateTime(), nullable=True),
        )

    # ── Production tables ─────────────────────────────────────────────────

    if not _table_exists("season_plans"):
        op.create_table(
            'season_plans',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('crop', sa.String(), nullable=False),
            sa.Column('season_year', sa.Integer(), nullable=False),
            sa.Column('predicted_yield', sa.Float(), nullable=True),
            sa.Column('confidence_score', sa.Float(), nullable=True),
            sa.Column('plan_details', sa.JSON(), nullable=True),
            sa.Column('status', sa.String(), server_default='active'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        )

    if not _table_exists("harvest_batches"):
        op.create_table(
            'harvest_batches',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('crop', sa.String(), nullable=False),
            sa.Column('quantity', sa.Float(), nullable=False),
            sa.Column('unit', sa.String(), server_default='kg'),
            sa.Column('prev_hash', sa.String(), nullable=True),
            sa.Column('current_hash', sa.String(), nullable=False),
            sa.Column('inputs_used', sa.JSON(), nullable=True),
            sa.Column('harvest_date', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('qr_code_url', sa.String(), nullable=True),
            sa.Column('certification_status', sa.String(), server_default='unverified'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        )

    if not _table_exists("sustainability_metrics"):
        op.create_table(
            'sustainability_metrics',
            sa.Column('id', sa.String(36), primary_key=True, nullable=False),
            sa.Column('user_id', sa.String(), nullable=False),
            sa.Column('carbon_score', sa.Float(), server_default='0.0'),
            sa.Column('co2_offset_kg', sa.Float(), server_default='0.0'),
            sa.Column('verified_practices', sa.JSON(), nullable=True),
            sa.Column('last_calculated', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    if op.get_context().dialect.name != "sqlite":
        return

    for table in [
        'sustainability_metrics', 'harvest_batches', 'season_plans',
        'helpline_call_logs', 'report_images', 'damage_reports', 'insurance_providers',
        'product_scans', 'verified_products', 'dealer_inventory', 'dealers',
        'escalation_queue', 'answer_upvotes', 'community_answers',
        'agricultural_experts', 'community_questions',
    ]:
        try:
            op.drop_table(table)
        except Exception:
            pass
