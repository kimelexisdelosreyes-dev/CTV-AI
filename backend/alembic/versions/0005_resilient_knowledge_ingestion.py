"""resilient knowledge ingestion

Revision ID: 0005
Revises: 0004
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("knowledge_documents", sa.Column("stage", sa.String(50), nullable=True))
    op.add_column("knowledge_documents", sa.Column("progress_percent", sa.Integer(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("page_count", sa.Integer(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("pages_processed", sa.Integer(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("ocr_pages", sa.Integer(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("knowledge_documents", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "knowledge_documents",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    )

    op.execute(
        """
        UPDATE knowledge_documents
        SET stage = CASE
            WHEN status = 'ready' THEN 'ready'
            WHEN status = 'failed' THEN 'failed'
            ELSE 'queued'
        END,
        progress_percent = CASE WHEN status = 'ready' THEN 100 ELSE 0 END,
        page_count = 0,
        pages_processed = 0,
        ocr_pages = 0
        """
    )

    for column in ("stage","progress_percent","page_count","pages_processed","ocr_pages","updated_at"):
        op.alter_column("knowledge_documents", column, nullable=False)

    op.create_index(
        op.f("ix_knowledge_documents_stage"),
        "knowledge_documents",
        ["stage"],
        unique=False,
    )

def downgrade() -> None:
    op.drop_index(op.f("ix_knowledge_documents_stage"), table_name="knowledge_documents")
    for column in (
        "updated_at","completed_at","started_at","ocr_pages","pages_processed",
        "page_count","progress_percent","stage"
    ):
        op.drop_column("knowledge_documents", column)
