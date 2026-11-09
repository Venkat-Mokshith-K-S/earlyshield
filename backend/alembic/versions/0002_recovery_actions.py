"""Module 5: create recovery_actions table

Revision ID: 0002_recovery_actions
Revises: 0001_create_users_table
Create Date: 2026-10-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Keep revision IDs <= 32 chars: alembic_version.version_num is VARCHAR(32)
# (Postgres enforces it; SQLite, used by the tests, silently doesn't).
revision = "0002_recovery_actions"
down_revision = "0001_create_users_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recovery_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("triggered_by", sa.String(length=255), nullable=False, server_default="auto"),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recovery_actions_incident_id", "recovery_actions", ["incident_id"])
    op.create_index("ix_recovery_actions_created_at", "recovery_actions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_recovery_actions_created_at", table_name="recovery_actions")
    op.drop_index("ix_recovery_actions_incident_id", table_name="recovery_actions")
    op.drop_table("recovery_actions")
