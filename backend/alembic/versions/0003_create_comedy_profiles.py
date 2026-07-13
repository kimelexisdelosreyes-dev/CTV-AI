"""create comedy profiles

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "comedy_profiles",
        sa.Column("user_email", sa.String(length=320), nullable=False),
        sa.Column("preferred_language", sa.String(length=50), nullable=False),
        sa.Column("humor_level", sa.String(length=50), nullable=False),
        sa.Column("likes_json", sa.Text(), nullable=False),
        sa.Column("safe_roast_topics_json", sa.Text(), nullable=False),
        sa.Column("off_limit_topics_json", sa.Text(), nullable=False),
        sa.Column("consent_to_roasting", sa.Boolean(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_email"),
    )


def downgrade() -> None:
    op.drop_table("comedy_profiles")
