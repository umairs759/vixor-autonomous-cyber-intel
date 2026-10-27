"""FindingScore model (T-013).

ML risk score (0-100) with SHAP explanations and narrative.
scored_by distinguishes ML-scored vs fallback rule-based.
"""

import enum
from typing import Any

from sqlalchemy import JSON, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ScoredBy(str, enum.Enum):
    ml = "ml"
    fallback = "fallback"


class RiskClass(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class FindingScore(Base):
    __tablename__ = "finding_scores"

    finding_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("findings.id"), primary_key=True
    )
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_class: Mapped[RiskClass] = mapped_column(
        Enum(RiskClass, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    shap_values: Mapped[dict[str, float]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    scored_by: Mapped[ScoredBy] = mapped_column(
        Enum(ScoredBy, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )

    finding: Mapped["Finding"] = relationship("Finding", back_populates="score")

    def __repr__(self) -> str:
        return f"<FindingScore(finding_id={self.finding_id}, risk_score={self.risk_score})>"


# Import all forward-referenced models to resolve relationship string names
from app.models.finding import Finding
