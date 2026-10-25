"""VIXOR — Ownership & IDOR prevention (Security 2).

Reusable dependency/repository pattern for row-level data ownership.
Every query touching projects, domains, assets, scans, findings,
correlations, reports, schedules must be scoped through the owning
project. Returns 404 (not 403) for resources the user does not own.
"""

from typing import TypeVar

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Query

T = TypeVar("T")


def get_owned_or_404(
    query: Query[T],
    user_id: str,
    user_role: str,
    resource_name: str = "resource",
) -> T:
    """Apply ownership filter to a query and return the first result or 404.

    Admins can see all resources; other users only see resources they own.
    Returns 404 (not 403) to avoid information leakage about resource
    existence.
    """
    if user_role != "admin":
        # Filter by ownership - subclasses should implement via
        # project-scoped queries. This is the base implementation that
        # filters by a user_id column if present.
        query = query.filter_by(user_id=user_id)

    result = query.first()
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_name} not found",
        )
    return result


def check_ownership(
    user_id: str,
    user_role: str,
    resource_owner_id: str | None,
    resource_name: str = "resource",
) -> None:
    """Check if a user owns a resource or is an admin.

    Raises 404 if the user doesn't own the resource and isn't an admin.
    """
    if user_role == "admin":
        return
    if resource_owner_id is None or resource_owner_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource_name} not found",
        )


def get_current_user_id(
    current_user: dict = Depends(lambda: {"user_id": "", "role": "viewer"}),
) -> dict:
    """Extract user ID and role from the current user dependency."""
    return current_user
