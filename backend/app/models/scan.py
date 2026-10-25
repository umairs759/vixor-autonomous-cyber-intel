"""Scan model (T-012).

A scan run against assets in a domain. Status tracks the pipeline state.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class ScanStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    partial = "partial"
    completed = "completed"
    failed = "failed"


class Scan(Base, TimestampMixin):
    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    domain_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    triggered_by: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    status: Mapped[ScanStatus] = mapped_column(
        Enum(ScanStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ScanStatus.queued,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship("Project", back_populates="scans")  # noqa: F821
    domain: Mapped["Domain"] = relationship("Domain", back_populates="scans")  # noqa: F821
    triggered_by_user: Mapped["User"] = relationship(  # noqa: F821
        "User", back_populates="triggered_scans"
    )
    scan_assets: Mapped[list["ScanAsset"]] = relationship(  # noqa: F821
        "ScanAsset", back_populates="scan", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(  # noqa: F821
        "Finding", back_populates="scan", cascade="all, delete-orphan"
    )
    correlations: Mapped[list["Correlation"]] = relationship(  # noqa: F821
        "Correlation", back_populates="scan", cascade="all, delete-orphan"
    )
    report: Mapped[Optional["Report"]] = relationship(  # noqa: F821
        "Report", back_populates="scan", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Scan(id={self.id}, status={self.status})>"
