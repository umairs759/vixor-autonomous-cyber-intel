"""VIXOR — Audit logging service (T-008).

Append-only audit log for every state-changing action.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    user_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Write an append-only audit log entry.

    Never updates or deletes existing entries.
    """
    entry = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        ip=ip,
        user_agent=user_agent,
        event_metadata=metadata or {},
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
