"""VIXOR — Domain Pydantic schemas (T-018).

Request/response models for domain registration and verification.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class DomainResponse(BaseModel):
    id: str
    project_id: str
    root_domain: str
    verification_token: str | None
    verification_method: str | None
    status: str
    verified_at: datetime | None
    last_reverified_at: datetime | None
    created_at: datetime


class RegisterDomainRequest(BaseModel):
    root_domain: str = Field(
        ...,
        min_length=1,
        max_length=253,
        description="Root domain to register (e.g., example.com)",
    )
    verification_method: str = Field(
        default="dns_txt",
        description="Verification method: dns_txt or file",
    )


class VerifyDomainRequest(BaseModel):
    verification_method: str = Field(
        ..., description="Verification method: dns_txt or file"
    )
