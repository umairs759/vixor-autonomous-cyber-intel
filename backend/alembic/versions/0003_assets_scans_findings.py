"""assets, scans, scan_assets, findings

Revision ID: 0003_assets_scans_findings
Revises: 0002_users_audit_projects_domains
Create Date: 2026-10-25 00:00:00.000000

T-012: Models and migrations for assets, scans, scan_assets, findings.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_assets_scans_findings"
down_revision: str | None = "0002_users_audit_projects_domains"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # assets table
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("domain_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("hostname", sa.String(length=253), nullable=False),
        sa.Column("ips", sa.JSON(), nullable=True),
        sa.Column("is_live", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "scope_status",
            sa.Enum("in_scope", "out_of_scope", name="scopestatus"),
            nullable=False,
            server_default="out_of_scope",
        ),
        sa.Column("scope_reason", sa.String(length=255), nullable=True),
        sa.Column("technologies", sa.JSON(), nullable=True),
        sa.Column("sensitivity_score", sa.Float(), nullable=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("domain_id", "hostname", name="uq_domain_hostname"),
    )
    op.create_index(op.f("ix_assets_domain_id"), "assets", ["domain_id"])
    op.create_index(op.f("ix_assets_hostname"), "assets", ["hostname"])
    op.create_index(op.f("ix_assets_scope_status"), "assets", ["scope_status"])

    # scans table
    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("domain_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "queued", "running", "partial", "completed", "failed", name="scanstatus"
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_scans_project_id"), "scans", ["project_id"])
    op.create_index(op.f("ix_scans_domain_id"), "scans", ["domain_id"])
    op.create_index(op.f("ix_scans_triggered_by"), "scans", ["triggered_by"])
    op.create_index(op.f("ix_scans_status"), "scans", ["status"])

    # scan_assets table
    op.create_table(
        "scan_assets",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="pending"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_scan_assets_scan_id"), "scan_assets", ["scan_id"])
    op.create_index(op.f("ix_scan_assets_asset_id"), "scan_assets", ["asset_id"])

    # findings table
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("fingerprint", sa.String(length=255), nullable=False),
        sa.Column(
            "source_tool",
            sa.Enum("nmap", "zap", "nuclei", name="sourcetool"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity_raw", sa.String(length=50), nullable=False),
        sa.Column("cvss", sa.Float(), nullable=True),
        sa.Column("cve_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("remediation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_findings_asset_id"), "findings", ["asset_id"])
    op.create_index(op.f("ix_findings_scan_id"), "findings", ["scan_id"])
    op.create_index(op.f("ix_findings_fingerprint"), "findings", ["fingerprint"])


def downgrade() -> None:
    op.drop_table("findings")
    op.drop_table("scan_assets")
    op.drop_table("scans")
    op.drop_table("assets")
    # Drop enum types (PostgreSQL only)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS sourcetool")
        op.execute("DROP TYPE IF EXISTS scanstatus")
        op.execute("DROP TYPE IF EXISTS scopestatus")
