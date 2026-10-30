"""Allow queued scans to be explicitly cancelled."""
from collections.abc import Sequence

from alembic import op

revision: str = "0005_scan_cancelled_status"
down_revision: str | None = "0004_scores_history_correlations_reports_schedules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE scanstatus ADD VALUE IF NOT EXISTS 'cancelled'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely in-place.
    pass
