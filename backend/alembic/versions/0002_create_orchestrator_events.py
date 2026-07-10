"""create orchestrator events

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orchestrator_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_email", sa.String(length=320), nullable=False),
        sa.Column("message_preview", sa.Text(), nullable=False),
        sa.Column("selected_assistant", sa.String(length=50), nullable=False),
        sa.Column("selected_model", sa.String(length=200), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_orchestrator_events_selected_assistant"),
        "orchestrator_events",
        ["selected_assistant"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orchestrator_events_user_email"),
        "orchestrator_events",
        ["user_email"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_orchestrator_events_user_email"),
        table_name="orchestrator_events",
    )
    op.drop_index(
        op.f("ix_orchestrator_events_selected_assistant"),
        table_name="orchestrator_events",
    )
    op.drop_table("orchestrator_events")
