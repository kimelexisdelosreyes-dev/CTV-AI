"""atomic operations snapshot lifecycle

Revision ID: 0011
Revises: 0010
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = (
        sa.Column("generated_at", sa.DateTime(timezone=True)),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("source_revision", sa.String(200)),
        sa.Column("board_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("source_item_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("refresh_duration_ms", sa.Float()),
        sa.Column("triggered_by", sa.String(320)),
        sa.Column("trigger_type", sa.String(30)),
        sa.Column(
            "previous_snapshot_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operations_snapshots.id", ondelete="SET NULL"),
        ),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("content_changed", sa.Boolean()),
        sa.Column(
            "semantic_cache_invalidated",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "cache_invalidation_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    for column in columns:
        op.add_column("operations_snapshots", column)
    op.create_index(
        "ix_operations_snapshots_content_hash",
        "operations_snapshots",
        ["content_hash"],
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id, row_number() OVER (
                ORDER BY fetched_at DESC NULLS LAST, created_at DESC
            ) AS position
            FROM operations_snapshots
            WHERE status = 'success'
        )
        UPDATE operations_snapshots AS snapshots
        SET status = CASE WHEN ranked.position = 1 THEN 'active' ELSE 'retired' END,
            generated_at = COALESCE(snapshots.fetched_at, snapshots.completed_at),
            activated_at = CASE
                WHEN ranked.position = 1 THEN COALESCE(snapshots.fetched_at, snapshots.completed_at)
                ELSE NULL
            END,
            trigger_type = COALESCE(snapshots.metadata_json->>'sync_trigger', 'legacy')
        FROM ranked
        WHERE snapshots.id = ranked.id
        """
    )
    op.execute("UPDATE operations_snapshots SET status = 'pending' WHERE status = 'running'")
    op.create_index(
        "uq_operations_snapshots_one_active",
        "operations_snapshots",
        ["status"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_operations_snapshots_one_active", table_name="operations_snapshots")
    op.execute("UPDATE operations_snapshots SET status = 'success' WHERE status = 'active'")
    op.execute("UPDATE operations_snapshots SET status = 'success' WHERE status = 'retired'")
    op.execute("UPDATE operations_snapshots SET status = 'running' WHERE status = 'pending'")
    op.drop_index("ix_operations_snapshots_content_hash", table_name="operations_snapshots")
    for name in (
        "cache_invalidation_count",
        "semantic_cache_invalidated",
        "content_changed",
        "attempt_count",
        "previous_snapshot_id",
        "trigger_type",
        "triggered_by",
        "refresh_duration_ms",
        "source_item_count",
        "board_count",
        "source_revision",
        "content_hash",
        "activated_at",
        "generated_at",
    ):
        op.drop_column("operations_snapshots", name)
