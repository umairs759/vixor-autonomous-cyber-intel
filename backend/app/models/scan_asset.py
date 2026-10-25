"""ScanAsset association model (T-012).

Links a scan to the assets it scanned, with per-asset status.
"""

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, generate_uuid


class ScanAsset(Base):
    __tablename__ = "scan_assets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    scan_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    scan: Mapped["Scan"] = relationship("Scan", back_populates="scan_assets")  # noqa: F821
    asset: Mapped["Asset"] = relationship("Asset", back_populates="scan_assets")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ScanAsset(scan_id={self.scan_id}, asset_id={self.asset_id}, status={self.status})>"
