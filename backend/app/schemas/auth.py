"""VIXOR — Auth Pydantic schemas (T-015).

Request/response models for login, refresh, and logout.
"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="Signed JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token lifetime in seconds")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Opaque refresh token")


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., description="Refresh token to revoke")
