"""VIXOR — Project Pydantic schemas (T-017).

Request/response models for project management with ownership checks.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectResponse(BaseModel):
    id: str
    owner_id: str
    name: str
    description: str | None
    created_at: datetime


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Project name")
    description: str | None = Field(
        default=None, max_length=1000, description="Project description"
    )


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=200, description="Project name"
    )
    description: str | None = Field(
        default=None, max_length=1000, description="Project description"
    )
