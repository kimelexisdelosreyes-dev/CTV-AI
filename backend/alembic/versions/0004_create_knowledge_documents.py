"""create knowledge documents

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-13
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("stored_path", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("uploaded_by", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_knowledge_documents_category"), "knowledge_documents", ["category"], unique=False)
    op.create_index(op.f("ix_knowledge_documents_status"), "knowledge_documents", ["status"], unique=False)
    op.create_index(op.f("ix_knowledge_documents_uploaded_by"), "knowledge_documents", ["uploaded_by"], unique=False)

def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_documents_uploaded_by"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_status"), table_name="knowledge_documents")
    op.drop_index(op.f("ix_knowledge_documents_category"), table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
