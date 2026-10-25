"""Correlation model (T-013).

Groups related findings into attack narratives with a combined score.
"""

from typing import Any, Optional
from sqlalchemy import String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base, TimestampMixin, generate_uuid


class Correlation(Base, TimestampMixin):
    __tablename__ = "correlations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    scan_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    asset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    combined_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    finding_ids: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    scan: Mapped["Scan"] = relationship("Scan", back_populates="correlations")
    asset: Mapped["Asset"] = relationship("Asset")

    def __repr__(self) -> str:
        return f"<Correlation(id={self.id}, title={self.title})>"
