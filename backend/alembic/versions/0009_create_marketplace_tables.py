"""create_marketplace_tables

Revision ID: 0009_create_marketplace_tables
Revises: 0008_create_community_qa_tables
Create Date: 2026-05-02 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0009_create_marketplace_tables'
down_revision = '0008_create_community_qa_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'dealers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('location_lat', sa.Float(), nullable=False),
        sa.Column('location_lon', sa.Float(), nullable=False),
        sa.Column('location_geom', Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('verification_status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
        sa.Column('verified_by', sa.String(length=128), nullable=True),
        sa.Column('regions_served', postgresql.JSON(), nullable=True),
        sa.Column('registration_date', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_dealers_location'), 'dealers', ['location_lat', 'location_lon'], unique=False)
    op.create_index(op.f('ix_dealers_verification'), 'dealers', ['is_verified', 'verification_status'], unique=False)

    op.create_table(
        'dealer_inventory',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('dealer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('dealers.id'), nullable=False),
        sa.Column('product_name', sa.String(length=200), nullable=False),
        sa.Column('input_type', sa.String(length=50), nullable=False),
        sa.Column('crop_type', sa.String(length=50), nullable=True),
        sa.Column('batch_number', sa.String(length=100), nullable=True),
        sa.Column('manufacturer', sa.String(length=200), nullable=True),
        sa.Column('quantity_in_stock', sa.Integer(), nullable=False),
        sa.Column('price_bdt', sa.Float(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=False),
        sa.Column('added_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_dealer_inventory_type_crop'), 'dealer_inventory', ['input_type', 'crop_type'], unique=False)
    op.create_index(op.f('ix_dealer_inventory_expiry'), 'dealer_inventory', ['expiry_date'], unique=False)

    op.create_table(
        'verified_products',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('barcode', sa.String(length=50), nullable=False),
        sa.Column('qr_code', sa.String(length=500), nullable=True),
        sa.Column('product_name', sa.String(length=200), nullable=False),
        sa.Column('manufacturer', sa.String(length=200), nullable=False),
        sa.Column('batch_number', sa.String(length=100), nullable=False),
        sa.Column('active_ingredient', sa.Text(), nullable=True),
        sa.Column('npk_ratio', sa.String(length=20), nullable=True),
        sa.Column('dose_per_application', sa.String(length=100), nullable=True),
        sa.Column('registered_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=False),
        sa.Column('government_registry', sa.String(length=50), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('verification_source', sa.String(length=50), nullable=False, server_default='local_db'),
    )
    op.create_index(op.f('ix_verified_products_expiry'), 'verified_products', ['expiry_date'], unique=False)
    op.create_index(op.f('ix_verified_products_barcode'), 'verified_products', ['barcode'], unique=False)
    op.create_index(op.f('ix_verified_products_batch'), 'verified_products', ['batch_number'], unique=False)

    op.create_table(
        'product_scans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('farmer_id_hashed', sa.String(length=128), nullable=False),
        sa.Column('barcode', sa.String(length=50), nullable=True),
        sa.Column('qr_text', sa.String(length=500), nullable=True),
        sa.Column('verified_product_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('verified_products.id'), nullable=True),
        sa.Column('verification_result', sa.String(length=50), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('scanned_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('location_lat', sa.Float(), nullable=True),
        sa.Column('location_lon', sa.Float(), nullable=True),
    )
    op.create_index(op.f('ix_product_scans_verified'), 'product_scans', ['verified_product_id', 'verification_result'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_product_scans_verified'), table_name='product_scans')
    op.drop_table('product_scans')
    op.drop_index(op.f('ix_verified_products_batch'), table_name='verified_products')
    op.drop_index(op.f('ix_verified_products_barcode'), table_name='verified_products')
    op.drop_index(op.f('ix_verified_products_expiry'), table_name='verified_products')
    op.drop_table('verified_products')
    op.drop_index(op.f('ix_dealer_inventory_expiry'), table_name='dealer_inventory')
    op.drop_index(op.f('ix_dealer_inventory_type_crop'), table_name='dealer_inventory')
    op.drop_table('dealer_inventory')
    op.drop_index(op.f('ix_dealers_verification'), table_name='dealers')
    op.drop_index(op.f('ix_dealers_location'), table_name='dealers')
    op.drop_table('dealers')
