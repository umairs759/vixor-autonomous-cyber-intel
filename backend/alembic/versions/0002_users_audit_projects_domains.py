"""users, audit_logs, projects, domains

Revision ID: 0002_users_audit_projects_domains
Revises: 0001_base_schema
Create Date: 2026-10-25 00:00:00.000000

T-011: Models and migrations for users, audit_logs, projects, domains.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_users_audit_projects_domains"
down_revision: Union[str, None] = "0001_base_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("admin", "analyst", "viewer", name="userrole"),
            nullable=False,
            server_default="analyst",
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    # audit_logs table (append-only)
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("metadata", postgresql.JSONB(as_text_type=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"])
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"])
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"])

    # projects table
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(op.f("ix_projects_owner_id"), "projects", ["owner_id"])

    # domains table
    op.create_table(
        "domains",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("root_domain", sa.String(length=253), nullable=False),
        sa.Column("verification_token", sa.String(length=255), nullable=False),
        sa.Column(
            "verification_method",
            sa.Enum("dns_txt", "file", name="verificationmethod"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("unverified", "verified", "suspended", name="domainstatus"),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reverified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "project_id", "root_domain", name="uq_project_root_domain"
        ),
    )
    op.create_index(op.f("ix_domains_project_id"), "domains", ["project_id"])
    op.create_index(op.f("ix_domains_root_domain"), "domains", ["root_domain"])
    op.create_index(op.f("ix_domains_status"), "domains", ["status"])


def downgrade() -> None:
    op.drop_table("domains")
    op.drop_table("projects")
    op.drop_table("audit_logs")
    op.drop_table("users")
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS domainstatus")
    op.execute("DROP TYPE IF EXISTS verificationmethod")
    op.execute("DROP TYPE IF EXISTS userrole")
