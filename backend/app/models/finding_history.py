"""FindingHistory model (T-013).

Tracks regression status of a finding across scan cycles:
NEW, RECURRING, REINTRODUCED, RESOLVED.
"""

import enum

from sqlalchemy import Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class HistoryStatus(str, enum.Enum):
    new = "new"
    recurring = "recurring"
    reintroduced = "reintroduced"
    resolved = "resolved"


class FindingHistory(Base, TimestampMixin):
    __tablename__ = "finding_history"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    scan_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    status: Mapped[HistoryStatus] = mapped_column(
        Enum(HistoryStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )

    asset: Mapped["Asset"] = relationship("Asset")  # noqa: F821
    scan: Mapped["Scan"] = relationship("Scan")  # noqa: F821

    def __repr__(self) -> str:
        return f"<FindingHistory(fingerprint={self.fingerprint}, status={self.status})>"
