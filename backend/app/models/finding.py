"""Finding model (T-012).

A unified finding normalized from scanner output. Deduplicated by fingerprint.
"""

import enum
from typing import Any, Optional

from sqlalchemy import Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class SourceTool(str, enum.Enum):
    nmap = "nmap"
    zap = "zap"
    nuclei = "nuclei"


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    asset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    scan_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_tool: Mapped[SourceTool] = mapped_column(
        Enum(SourceTool, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity_raw: Mapped[str] = mapped_column(String(50), nullable=False)
    cvss: Mapped[float | None] = mapped_column(nullable=True)
    cve_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="findings")  # noqa: F821
    scan: Mapped["Scan"] = relationship("Scan", back_populates="findings")  # noqa: F821
    score: Mapped[Optional["FindingScore"]] = relationship(  # noqa: F821
        "FindingScore",
        back_populates="finding",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Finding(id={self.id}, title={self.title}, tool={self.source_tool})>"
