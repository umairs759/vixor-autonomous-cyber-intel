"""Domain model (T-011).

Represents a verified root domain owned by a project.
Status: unverified -> verified -> suspended (on re-verification failure).
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class DomainStatus(str, enum.Enum):
    unverified = "unverified"
    verified = "verified"
    suspended = "suspended"


class VerificationMethod(str, enum.Enum):
    dns_txt = "dns_txt"
    file = "file"


class Domain(Base, TimestampMixin):
    __tablename__ = "domains"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False, index=True
    )
    root_domain: Mapped[str] = mapped_column(String(253), nullable=False, index=True)
    verification_token: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_method: Mapped[VerificationMethod] = mapped_column(
        Enum(VerificationMethod, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    status: Mapped[DomainStatus] = mapped_column(
        Enum(DomainStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=DomainStatus.unverified,
        nullable=False,
        index=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_reverified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("project_id", "root_domain", name="uq_project_root_domain"),
    )

    project: Mapped["Project"] = relationship("Project", back_populates="domains")
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", back_populates="domain", cascade="all, delete-orphan"
    )
    scans: Mapped[list["Scan"]] = relationship(
        "Scan", back_populates="domain", cascade="all, delete-orphan"
    )
    schedules: Mapped[list["ScanSchedule"]] = relationship(
        "ScanSchedule", back_populates="domain", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Domain(id={self.id}, root_domain={self.root_domain}, status={self.status})>"


# Import all forward-referenced models to resolve relationship string names
from app.models.asset import Asset
from app.models.project import Project
from app.models.scan import Scan
from app.models.schedule import ScanSchedule
