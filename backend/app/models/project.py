"""Project model (T-011).

A project groups domains, assets, scans, and findings. Owned by a user.
"""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="owned_projects")
    domains: Mapped[list["Domain"]] = relationship(
        "Domain", back_populates="project", cascade="all, delete-orphan"
    )
    scans: Mapped[list["Scan"]] = relationship(
        "Scan", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"


# Import all forward-referenced models to resolve relationship string names
from app.models.domain import Domain
from app.models.scan import Scan
from app.models.user import User
