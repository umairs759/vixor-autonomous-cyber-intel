"""finding_scores, finding_history, correlations, reports, scan_schedules

Revision ID: 0004_scores_history_correlations_reports_schedules
Revises: 0003_assets_scans_findings
Create Date: 2026-10-25 00:00:00.000000

T-013: Models and migrations for finding_scores, finding_history,
correlations, reports, scan_schedules.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_scores_history_correlations_reports_schedules"
down_revision: str | None = "0003_assets_scans_findings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # finding_scores table
    op.create_table(
        "finding_scores",
        sa.Column("finding_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column(
            "risk_class",
            sa.Enum("low", "medium", "high", "critical", name="riskclass"),
            nullable=False,
        ),
        sa.Column("model_version", sa.String(length=50), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("shap_values", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column(
            "scored_by",
            sa.Enum("ml", "fallback", name="scoredby"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("finding_id"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
    )

    # finding_history table
    op.create_table(
        "finding_history",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("fingerprint", sa.String(length=255), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "new", "recurring", "reintroduced", "resolved", name="historystatus"
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_finding_history_fingerprint"), "finding_history", ["fingerprint"]
    )
    op.create_index(
        op.f("ix_finding_history_asset_id"), "finding_history", ["asset_id"]
    )
    op.create_index(op.f("ix_finding_history_scan_id"), "finding_history", ["scan_id"])

    # correlations table
    op.create_table(
        "correlations",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("combined_score", sa.Float(), nullable=True),
        sa.Column("finding_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_correlations_scan_id"), "correlations", ["scan_id"])
    op.create_index(op.f("ix_correlations_asset_id"), "correlations", ["asset_id"])

    # reports table
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("generated_by", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("ix_reports_scan_id"), "reports", ["scan_id"])
    op.create_index(op.f("ix_reports_generated_by"), "reports", ["generated_by"])

    # scan_schedules table
    op.create_table(
        "scan_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("domain_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("cron", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["domain_id"], ["domains.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("ix_scan_schedules_domain_id"), "scan_schedules", ["domain_id"]
    )


def downgrade() -> None:
    op.drop_table("scan_schedules")
    op.drop_table("reports")
    op.drop_table("correlations")
    op.drop_table("finding_history")
    op.drop_table("finding_scores")
    # Drop enum types (PostgreSQL only)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS scoredby")
        op.execute("DROP TYPE IF EXISTS historystatus")
        op.execute("DROP TYPE IF EXISTS riskclass")
