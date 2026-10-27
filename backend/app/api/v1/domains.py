"""VIXOR — Domains API endpoints (T-018, T-019).

POST /projects/{id}/domains — register a domain (generates random token).
POST /domains/{id}/verify — verify ownership via DNS TXT or .well-known file.
GET /domains/{id} — get domain details (ownership-checked).

All endpoints enforce ownership checks (IDOR protection).
"""

from typing import Any

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rbac import require_role
from app.deps import get_db
from app.redis import get_redis
from app.schemas.domain import (
    DomainResponse,
    RegisterDomainRequest,
    VerifyDomainRequest,
)
from app.services.auth_service import AuthService
from app.services.domain_service import DomainService
from app.services.domain_verification import perform_verification

router = APIRouter(prefix="/projects", tags=["domains"])


def get_domain_service(db: Session = Depends(get_db)) -> DomainService:
    return DomainService(db=db)


def get_auth_service(
    db: Session = Depends(get_db),
    redis: redis.Redis = Depends(get_redis),
) -> AuthService:
    return AuthService(db=db, redis_client=redis)


@router.post(
    "/{project_id}/domains",
    response_model=DomainResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a domain under a project (generates verification token)",
)
async def register_domain(
    request: Request,
    project_id: str,
    domain_data: RegisterDomainRequest,
    domain_svc: DomainService = Depends(get_domain_service),
    auth: AuthService = Depends(get_auth_service),
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> DomainResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Verify project ownership before allowing domain registration
    from app.services.project_service import ProjectService

    project_svc = ProjectService(auth.db)
    project = project_svc.get_project(
        project_id=project_id,
        user_id=current_user["user_id"],
        user_role=current_user.get("role", "viewer"),
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    domain = domain_svc.register_domain(
        project_id=project_id,
        user_id=current_user["user_id"],
        root_domain=domain_data.root_domain,
        verification_method=domain_data.verification_method,
        ip=client_ip,
        user_agent=user_agent,
    )
    return DomainResponse(
        id=domain.id,
        project_id=domain.project_id,
        root_domain=domain.root_domain,
        verification_token=domain.verification_token,
        verification_method=domain.verification_method.value,
        status=domain.status.value,
        verified_at=domain.verified_at,
        last_reverified_at=domain.last_reverified_at,
        created_at=domain.created_at,
    )


@router.get(
    "/{project_id}/domains",
    response_model=list[DomainResponse],
    summary="List domains for a project (ownership-checked)",
)
async def list_domains(
    project_id: str,
    domain_svc: DomainService = Depends(get_domain_service),
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> list[DomainResponse]:
    domains = domain_svc.list_domains(
        project_id=project_id,
        user_id=current_user["user_id"],
        user_role=current_user.get("role", "viewer"),
    )
    return [
        DomainResponse(
            id=d.id,
            project_id=d.project_id,
            root_domain=d.root_domain,
            verification_token=d.verification_token,
            verification_method=d.verification_method.value,
            status=d.status.value,
            verified_at=d.verified_at,
            last_reverified_at=d.last_reverified_at,
            created_at=d.created_at,
        )
        for d in domains
    ]


@router.post(
    "/domains/{domain_id}/verify",
    response_model=DomainResponse,
    summary="Verify domain ownership (DNS TXT or .well-known file)",
)
async def verify_domain(
    request: Request,
    domain_id: str,
    verify_data: VerifyDomainRequest,
    domain_svc: DomainService = Depends(get_domain_service),
    auth: AuthService = Depends(get_auth_service),
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> DomainResponse:
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    domain = domain_svc.get_domain(
        domain_id=domain_id,
        user_id=current_user["user_id"],
        user_role=current_user.get("role", "viewer"),
    )
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found.",
        )

    # Validate verification method
    from app.models.domain import VerificationMethod

    try:
        VerificationMethod(verify_data.verification_method)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification method. Use 'dns_txt' or 'file'.",
        )

    # Perform actual verification (DNS TXT or .well-known file)
    success, reason = await perform_verification(
        domain=domain,
        db=auth.db,
        user_id=current_user["user_id"],
        ip=client_ip,
        user_agent=user_agent,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=reason or "Verification failed.",
        )

    # Refresh domain from DB after perform_verification updated it
    auth.db.refresh(domain)

    return DomainResponse(
        id=domain.id,
        project_id=domain.project_id,
        root_domain=domain.root_domain,
        verification_token=domain.verification_token,
        verification_method=domain.verification_method.value,
        status=domain.status.value,
        verified_at=domain.verified_at,
        last_reverified_at=domain.last_reverified_at,
        created_at=domain.created_at,
    )


@router.get(
    "/domains/{domain_id}",
    response_model=DomainResponse,
    summary="Get domain details (ownership-checked)",
)
async def get_domain(
    domain_id: str,
    domain_svc: DomainService = Depends(get_domain_service),
    current_user: dict[str, Any] = Depends(require_role("viewer")),
) -> DomainResponse:
    domain = domain_svc.get_domain(
        domain_id=domain_id,
        user_id=current_user["user_id"],
        user_role=current_user.get("role", "viewer"),
    )
    if not domain:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Domain not found.",
        )
    return DomainResponse(
        id=domain.id,
        project_id=domain.project_id,
        root_domain=domain.root_domain,
        verification_token=domain.verification_token,
        verification_method=domain.verification_method.value,
        status=domain.status.value,
        verified_at=domain.verified_at,
        last_reverified_at=domain.last_reverified_at,
        created_at=domain.created_at,
    )
