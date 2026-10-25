"""Project model (T-011).

A project groups domains, assets, scans, and findings. Owned by a user.
"""

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, generate_uuid


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=generate_uuid
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped["User"] = relationship("User", back_populates="owned_projects")  # noqa: F821
    domains: Mapped[list["Domain"]] = relationship(  # noqa: F821
        "Domain", back_populates="project", cascade="all, delete-orphan"
    )
    scans: Mapped[list["Scan"]] = relationship(  # noqa: F821
        "Scan", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name})>"
