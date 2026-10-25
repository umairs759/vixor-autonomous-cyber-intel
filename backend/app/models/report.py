"""Report model (T-013).

PDF report generated from scan data. Download is ownership-checked
with an unguessable UUID4 ID.
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base, TimestampMixin, generate_uuid


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    scan_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    generated_by: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)

    scan: Mapped["Scan"] = relationship("Scan", back_populates="report")
    generated_by_user: Mapped["User"] = relationship(
        "User", back_populates="generated_reports"
    )

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, scan_id={self.scan_id})>"
