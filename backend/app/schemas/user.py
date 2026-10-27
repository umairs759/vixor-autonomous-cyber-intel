"""VIXOR — User Pydantic schemas (T-016).

Request/response models for user management (admin only).
"""

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: str


class CreateUserRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    role: str = Field(
        default="analyst", description="User role: admin, analyst, or viewer"
    )


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = Field(default=None, description="User email address")
    password: str | None = Field(
        default=None, min_length=8, description="User password"
    )
    role: str | None = Field(
        default=None, description="User role: admin, analyst, or viewer"
    )
    is_active: bool | None = Field(
        default=None, description="Whether the user is active"
    )


class AuditLogResponse(BaseModel):
    id: str
    user_id: str | None
    action: str
    resource_type: str
    resource_id: str | None
    ip: str | None
    user_agent: str | None
    metadata: dict[str, Any] | None
    created_at: str
