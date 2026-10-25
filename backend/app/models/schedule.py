"""ScanSchedule model (T-013).

Celery Beat schedule for recurring domain scans. Ownership re-verified
before each scheduled run.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class ScanSchedule(Base, TimestampMixin):
    __tablename__ = "scan_schedules"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    domain_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    cron: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    domain: Mapped["Domain"] = relationship("Domain", back_populates="schedules")  # noqa: F821

    def __repr__(self) -> str:
        return f"<ScanSchedule(id={self.id}, domain_id={self.domain_id}, cron={self.cron})>"
