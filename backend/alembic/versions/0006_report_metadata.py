"""Add report metadata used by current API and service."""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_report_metadata"
down_revision: str | None = "0005_scan_cancelled_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("title", sa.String(length=512), nullable=False, server_default=""))
    op.add_column("reports", sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"))
    op.add_column("reports", sa.Column("format", sa.String(length=50), nullable=False, server_default="PDF"))


def downgrade() -> None:
    op.drop_column("reports", "format")
    op.drop_column("reports", "status")
    op.drop_column("reports", "title")
