"""Refresh-token format, rotation validation, and logout revocation tests."""

import uuid
from unittest.mock import Mock

from app.core.security import create_access_token, decode_access_token
from app.services.auth_service import AuthService


def _service(redis_client=None):
    return AuthService(db=Mock(), redis_client=redis_client or Mock())


def test_refresh_token_is_signed_and_distinct_from_access_token():
    service = _service()
    user_id = str(uuid.uuid4())

    token = service._create_refresh_token(user_id, str(uuid.uuid4()))

    claims = decode_access_token(token)
    assert claims["sub"] == user_id
    assert claims["token_type"] == "refresh"
    assert claims["exp"] > claims["iat"]


def test_refresh_rejects_access_token(mocker):
    service = _service()
    mocker.patch("app.services.auth_service.write_audit_log")
    access_token = create_access_token(
        user_id=str(uuid.uuid4()), role="analyst", jti=str(uuid.uuid4())
    )

    result = service.refresh_access_token(access_token)

    assert result == (None, None, "Invalid refresh token.")


def test_logout_revokes_matching_refresh_token(mocker):
    redis_client = Mock()
    service = _service(redis_client)
    mocker.patch("app.services.auth_service.write_audit_log")
    user_id, token_jti = str(uuid.uuid4()), str(uuid.uuid4())
    token = service._create_refresh_token(user_id, token_jti)
    redis_client.get.return_value = service._hash_token(token)

    service.logout(user_id=None, refresh_token=token)

    redis_client.delete.assert_called_once_with(service._refresh_token_key(token_jti))
    redis_client.srem.assert_called_once_with(
        f"user_refresh_tokens:{user_id}", token_jti
    )
import pytest
import redis
from fastapi import HTTPException, Response
from starlette.requests import Request

from app.api.v1.auth import refresh
from app.schemas.auth import RefreshRequest


@pytest.mark.asyncio
async def test_refresh_returns_503_when_redis_is_unavailable(monkeypatch):
    class UnavailableAuth:
        def refresh_access_token(self, **kwargs):
            raise redis.exceptions.ConnectionError("redis unavailable")

    request = Request({
        "type": "http", "asgi": {"version": "3.0"},
        "http_version": "1.1", "method": "POST", "scheme": "http",
        "path": "/api/v1/auth/refresh", "raw_path": b"/api/v1/auth/refresh",
        "query_string": b"", "headers": [], "client": ("127.0.0.1", 1234),
        "server": ("127.0.0.1", 8001),
    })
    with pytest.raises(HTTPException) as error:
        await refresh(request, Response(), RefreshRequest(refresh_token="opaque"), UnavailableAuth())
    assert error.value.status_code == 503
    assert error.value.detail == "Token service is temporarily unavailable."
