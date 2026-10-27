"""VIXOR — Role-based access control (T-015).

RBAC dependencies for FastAPI. Roles: admin, analyst, viewer.
- admin: full access
- analyst: can run scans, view findings, manage own domains/projects
- viewer: read-only (executive summary, reports)
"""

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status

from app.deps import get_current_user


def require_role(required_role: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Return a dependency that requires the given role (or higher)."""

    role_hierarchy = {"viewer": 0, "analyst": 1, "admin": 2}

    def role_checker(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        user_role = current_user.get("role", "viewer")
        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this resource",
            )
        return current_user

    return role_checker


# Common dependencies
RequireAdmin = Annotated[dict[str, Any], Depends(require_role("admin"))]
RequireAnalyst = Annotated[dict[str, Any], Depends(require_role("analyst"))]
RequireViewer = Annotated[dict[str, Any], Depends(require_role("viewer"))]
