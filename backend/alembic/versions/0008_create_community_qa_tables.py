"""create_community_qa_tables

Revision ID: 0008_create_community_qa_tables
Revises: 0007_create_postgis_pgvector_extensions
Create Date: 2026-05-02 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '0008_create_community_qa_tables'
down_revision = '0007_create_postgis_pgvector_extensions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        return
        
    op.create_table(
        'community_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('farmer_id_hashed', sa.String(length=128), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_text_en', sa.Text(), nullable=True),
        sa.Column('crop_type', sa.String(length=50), nullable=False),
        sa.Column('growth_stage', sa.String(length=50), nullable=True),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lon', sa.Float(), nullable=False),
        sa.Column('location_geom', Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('moderation_flag', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('admin_review_needed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_community_questions_crop_stage'), 'community_questions', ['crop_type', 'growth_stage'], unique=False)
    op.create_index(op.f('ix_community_questions_status_created'), 'community_questions', ['status', 'created_at'], unique=False)
    op.create_index('idx_community_questions_embedding', 'community_questions', ['embedding'], postgresql_using='ivfflat')

    op.create_table(
        'community_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('community_questions.id'), nullable=False),
        sa.Column('answerer_id', sa.String(length=128), nullable=False),
        sa.Column('answerer_name', sa.String(length=100), nullable=False),
        sa.Column('answerer_credentials', sa.String(length=255), nullable=True),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('answer_text_en', sa.Text(), nullable=True),
        sa.Column('is_expert_answer', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=True),
    )
    op.create_index(op.f('ix_community_answers_question_answerer'), 'community_answers', ['question_id', 'answerer_id'], unique=False)

    op.create_table(
        'answer_upvotes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('answer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('community_answers.id'), nullable=False),
        sa.Column('farmer_id_hashed', sa.String(length=128), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f('ix_answer_upvotes_unique'), 'answer_upvotes', ['answer_id', 'farmer_id_hashed'], unique=True)

    op.create_table(
        'escalation_queue',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('community_questions.id'), nullable=False, unique=True),
        sa.Column('expert_id', sa.String(length=128), sa.ForeignKey('agricultural_experts.id'), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('auto_escalate_at', sa.DateTime(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'agricultural_experts',
        sa.Column('id', sa.String(length=128), primary_key=True, nullable=False),
        sa.Column('region_geom', Geometry(geometry_type='POINT', srid=4326), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('credentials', sa.String(length=255), nullable=True),
        sa.Column('areas_of_expertise', postgresql.JSON(), nullable=True),
        sa.Column('response_time_avg_hours', sa.Float(), nullable=True),
        sa.Column('total_answers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rating_avg', sa.Float(), nullable=False, server_default='4.0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('last_active_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    if op.get_context().dialect.name == "sqlite":
        return
        
    op.drop_table('agricultural_experts')
    op.drop_table('escalation_queue')
    op.drop_index(op.f('ix_answer_upvotes_unique'), table_name='answer_upvotes')
    op.drop_table('answer_upvotes')
    op.drop_index(op.f('ix_community_answers_question_answerer'), table_name='community_answers')
    op.drop_table('community_answers')
    op.drop_index('idx_community_questions_embedding', table_name='community_questions')
    op.drop_index(op.f('ix_community_questions_status_created'), table_name='community_questions')
    op.drop_index(op.f('ix_community_questions_crop_stage'), table_name='community_questions')
    op.drop_table('community_questions')
