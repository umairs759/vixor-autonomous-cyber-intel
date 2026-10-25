"""Asset model (T-012).

Represents a discovered host/asset under a domain. Scope status is
enforced by scope_guard before any scanning.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class ScopeStatus(str, enum.Enum):
    in_scope = "in_scope"
    out_of_scope = "out_of_scope"


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    domain_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("domains.id"), nullable=False, index=True
    )
    hostname: Mapped[str] = mapped_column(String(253), nullable=False, index=True)
    ips: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scope_status: Mapped[ScopeStatus] = mapped_column(
        Enum(ScopeStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ScopeStatus.out_of_scope,
        nullable=False,
        index=True,
    )
    scope_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    technologies: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    sensitivity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    first_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("domain_id", "hostname", name="uq_domain_hostname"),
    )

    domain: Mapped["Domain"] = relationship("Domain", back_populates="assets")
    findings: Mapped[list["Finding"]] = relationship(
        "Finding", back_populates="asset", cascade="all, delete-orphan"
    )
    scan_assets: Mapped[list["ScanAsset"]] = relationship(
        "ScanAsset", back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, hostname={self.hostname}, scope={self.scope_status})>"


# Import all forward-referenced models to resolve relationship string names
from app.models.domain import Domain
from app.models.finding import Finding
from app.models.scan_asset import ScanAsset
