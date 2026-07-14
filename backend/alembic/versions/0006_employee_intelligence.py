"""employee intelligence foundation

Revision ID: 0006
Revises: 0005
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    enums = [
        sa.Enum("trainee","beginner","intermediate","advanced","expert", name="experience_level"),
        sa.Enum("concise","step_by_step","detailed","visual","conversational", name="response_style"),
        sa.Enum("brief","standard","deep", name="detail_level"),
        sa.Enum("private","employee","manager","department","hr","company", name="memory_visibility"),
        sa.Enum("proposed","confirmed","rejected","archived", name="memory_status"),
        sa.Enum("trainee","beginner","intermediate","advanced","expert", name="skill_level"),
        sa.Enum("trainee","beginner","intermediate","advanced","expert", name="tool_proficiency"),
    ]
    bind = op.get_bind()
    for enum_type in enums:
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), unique=True, nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "employee_profiles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="SET NULL")),
        sa.Column("manager_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("job_title", sa.String(200)),
        sa.Column("experience_level", postgresql.ENUM(name="experience_level", create_type=False), nullable=False),
        sa.Column("primary_responsibilities", sa.Text()),
        sa.Column("specialties", sa.Text()),
        sa.Column("preferred_language", sa.String(50), nullable=False),
        sa.Column("response_style", postgresql.ENUM(name="response_style", create_type=False), nullable=False),
        sa.Column("detail_level", postgresql.ENUM(name="detail_level", create_type=False), nullable=False),
        sa.Column("profile_visibility", postgresql.ENUM(name="memory_visibility", create_type=False), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "employee_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("prefers_checklists", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("prefers_visual_examples", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("comfortable_with_technical_terms", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("preferred_output_format", sa.String(50), nullable=False, server_default="bullets"),
        sa.Column("requires_approval_for", sa.Text()),
        sa.Column("custom_instructions", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "employee_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("level", postgresql.ENUM(name="skill_level", create_type=False), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_employee_skill_name"),
    )

    op.create_table(
        "employee_tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("proficiency", postgresql.ENUM(name="tool_proficiency", create_type=False), nullable=False),
        sa.Column("primary_tool", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_employee_tool_name"),
    )

    op.create_table(
        "employee_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("memory_type", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("visibility", postgresql.ENUM(name="memory_visibility", create_type=False), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", postgresql.ENUM(name="memory_status", create_type=False), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    for table in (
        "employee_memories","employee_tools","employee_skills",
        "employee_preferences","employee_profiles","departments",
    ):
        op.drop_table(table)

    bind = op.get_bind()
    for name in (
        "tool_proficiency","skill_level","memory_status","memory_visibility",
        "detail_level","response_style","experience_level",
    ):
        postgresql.ENUM(name=name).drop(bind, checkfirst=True)
