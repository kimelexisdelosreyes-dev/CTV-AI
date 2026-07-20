"""semantic response cache

Revision ID: 0010
Revises: 0009
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "semantic_cache_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("normalized_question", sa.Text(), nullable=False),
        sa.Column("exact_key", sa.String(64), nullable=False),
        sa.Column("question_embedding", sa.JSON()),
        sa.Column("safe_answer", sa.Text(), nullable=False),
        sa.Column("safe_sources", sa.JSON(), nullable=False),
        sa.Column("personalization", sa.JSON(), nullable=False),
        sa.Column("context_route", sa.String(80), nullable=False),
        sa.Column("context_types", sa.JSON(), nullable=False),
        sa.Column("scope_type", sa.String(30), nullable=False),
        sa.Column("scope_key", sa.String(160), nullable=False),
        sa.Column("invalidation_fingerprint", sa.String(64), nullable=False),
        sa.Column("operations_fingerprint", sa.String(64)),
        sa.Column("knowledge_fingerprint", sa.String(64)),
        sa.Column("employee_fingerprint", sa.String(64)),
        sa.Column("conversation_fingerprint", sa.String(64)),
        sa.Column("model_role", sa.String(40)),
        sa.Column("model_name", sa.String(160)),
        sa.Column("result_type", sa.String(40), nullable=False),
        sa.Column("policy_version", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_hit_at", sa.DateTime(timezone=True)),
        sa.Column("hit_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_similarity", sa.Float()),
        sa.UniqueConstraint("exact_key", name="uq_semantic_cache_exact_key"),
    )
    op.create_index(
        "ix_semantic_cache_scope_expiry",
        "semantic_cache_entries",
        ["scope_key", "expires_at"],
    )
    op.create_index(
        "ix_semantic_cache_context_state",
        "semantic_cache_entries",
        ["scope_key", "invalidation_fingerprint", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_semantic_cache_context_state", table_name="semantic_cache_entries")
    op.drop_index("ix_semantic_cache_scope_expiry", table_name="semantic_cache_entries")
    op.drop_table("semantic_cache_entries")
