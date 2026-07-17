"""operations snapshots

Revision ID: 0008
Revises: 0007
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operations_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("failed_at", sa.DateTime(timezone=True)),
        sa.Column("error_category", sa.String(80)),
        sa.Column("safe_error", sa.String(300)),
        sa.Column("task_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_operations_snapshots_status", "operations_snapshots", ["status"])
    op.create_table(
        "operation_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("operations_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(120), nullable=False),
        sa.Column("board_id", sa.String(120)),
        sa.Column("board_name", sa.String(300)),
        sa.Column("group_id", sa.String(120)),
        sa.Column("group_name", sa.String(300)),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.String(200)),
        sa.Column("priority", sa.String(200)),
        sa.Column("assignee_ids", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at_source", sa.DateTime(timezone=True)),
        sa.Column("url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_operation_tasks_snapshot_id", "operation_tasks", ["snapshot_id"])
    op.create_index("ix_operation_tasks_external_id", "operation_tasks", ["external_id"])
    op.create_index("ix_operation_tasks_status", "operation_tasks", ["status"])
    op.create_index("ix_operation_tasks_priority", "operation_tasks", ["priority"])
    op.create_index("ix_operation_tasks_due_at", "operation_tasks", ["due_at"])
    op.create_index("ix_operation_tasks_snapshot_external", "operation_tasks", ["snapshot_id", "external_id"], unique=True)
    op.create_index("ix_operation_tasks_snapshot_status", "operation_tasks", ["snapshot_id", "status"])
    op.create_index("ix_operation_tasks_snapshot_due", "operation_tasks", ["snapshot_id", "due_at"])
    op.create_index("ix_operation_tasks_snapshot_priority", "operation_tasks", ["snapshot_id", "priority"])


def downgrade() -> None:
    op.drop_table("operation_tasks")
    op.drop_table("operations_snapshots")
