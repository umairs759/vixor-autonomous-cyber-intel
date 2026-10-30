"""Scan creation and response schemas."""

from pydantic import BaseModel, Field


class ScanCreateRequest(BaseModel):
    domain_id: str = Field(..., min_length=1)
    asset_ids: list[str] = Field(default_factory=list)
