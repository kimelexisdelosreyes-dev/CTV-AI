"""operation task owner index

Revision ID: 0009
Revises: 0008
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("operation_tasks", sa.Column("owner_key", sa.String(500)))
    op.create_index("ix_operation_tasks_owner_key", "operation_tasks", ["owner_key"])


def downgrade() -> None:
    op.drop_index("ix_operation_tasks_owner_key", "operation_tasks")
    op.drop_column("operation_tasks", "owner_key")
