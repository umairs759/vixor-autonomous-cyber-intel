"""VIXOR — WebSocket progress endpoints (T-031).

Authenticated WebSocket that subscribes to Redis pub/sub for scan
progress events and forwards them to the client.

Security:
- JWT token required (passed as ``?token=`` query parameter).
- Ownership check: client must have access to the scan's domain.
- Redis pub/sub channel is per-scan: ``scan:{scan_id}``.
- Non-blocking: the blocking Redis pub/sub loop runs in a worker thread
  via ``asyncio.to_thread`` and forwards messages through an asyncio.Queue.
"""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.security import decode_access_token
from app.deps import get_db_session
from app.models.domain import Domain
from app.models.scan import Scan
from app.redis import get_redis_client
from app.services.domain_service import DomainService

logger = get_logger("vixor.ws")

router = APIRouter(tags=["websocket"])

# Redis pub/sub channel prefix for scan progress
SCAN_CHANNEL_PREFIX = "scan:"


def _get_current_user_from_token(token: str) -> dict[str, Any] | None:
    """Decode a JWT token and return the user payload, or None on failure."""
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
        return {
            "user_id": user_id,
            "role": payload.get("role"),
            "jti": payload.get("jti"),
        }
    except Exception:  # noqa: BLE001 - any token failure rejects the socket
        logger.warning("websocket_token_invalid")
        return None


def _user_has_scan_access(user_id: str, scan: Scan, db_session: Session) -> bool:
    """Check whether the user can access the scan's domain."""
    try:
        domain = db_session.query(Domain).filter(Domain.id == scan.domain_id).first()
    except Exception:  # noqa: BLE001 - DB failures deny access
        return False
    if domain is None:
        return False

    domain_svc = DomainService(db=db_session)
    try:
        return (
            domain_svc.get_domain(
                domain_id=scan.domain_id,
                user_id=user_id,
                user_role="viewer",
            )
            is not None
        )
    except Exception:  # noqa: BLE001 - access check failures deny access
        return False


def _redis_pubsub_loop(
    channel: str,
    queue: "asyncio.Queue[str | None]",
    loop: asyncio.AbstractEventLoop,
) -> None:
    """Blocking Redis pub/sub listener (runs in a worker thread).

    Forwards each received message onto ``queue`` using the event loop,
    then puts ``None`` when the subscription ends or an error occurs.
    """
    try:
        redis = get_redis_client()
        redis_any: Any = redis
        pubsub = redis_any.pubsub()
        pubsub.subscribe(channel)

        while True:
            message = pubsub.get_message(timeout=1.0)
            if message is None:
                continue
            if message.get("type") == "subscribe":
                continue
            if message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                asyncio.run_coroutine_threadsafe(queue.put(data), loop)
    except Exception:  # listener failure ends the socket
        logger.exception("websocket_redis_listener_failed", channel=channel)
    finally:
        asyncio.run_coroutine_threadsafe(queue.put(None), loop)


@router.websocket("/scans/{scan_id}/ws")
async def scan_progress_ws(websocket: WebSocket, scan_id: str) -> None:
    """WebSocket endpoint for live scan progress.

    Query param ``token`` (JWT) is required. The client must have viewer+
    access to the scan's domain. Messages from the Redis ``scan:{scan_id}``
    channel are forwarded as JSON text frames.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    current_user = _get_current_user_from_token(token)
    if current_user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = current_user["user_id"]

    # Ownership check on the scan's domain
    db = get_db_session()
    try:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        if not _user_has_scan_access(user_id, scan, db):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    finally:
        db.close()

    await websocket.accept()

    channel = f"{SCAN_CHANNEL_PREFIX}{scan_id}"
    queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    listener_future = asyncio.ensure_future(
        asyncio.to_thread(_redis_pubsub_loop, channel, queue, loop)
    )

    try:
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
            except TimeoutError:
                # Send a heartbeat ping to keep the connection alive
                await websocket.send_text(
                    json.dumps({"type": "heartbeat", "scan_id": scan_id})
                )
                continue

            if message is None:
                # Listener ended
                break

            await websocket.send_text(message)
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", scan_id=scan_id, user_id=user_id)
    finally:
        listener_future.cancel()
        try:
            await listener_future
        except asyncio.CancelledError:
            pass
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001 - close may fail after disconnect
            logger.debug("websocket_close_failed", scan_id=scan_id)
