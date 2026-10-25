"""VIXOR — Projects API endpoints (T-017).

GET/POST /projects, GET/PATCH/DELETE /projects/{id}.
Ownership checks enforced: admins see all, others see only their own.
Returns 404 (not 403) for resources the user does not own (IDOR protection).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rbac import RequireViewer
from app.deps import get_db
from app.redis import get_redis
from app.schemas.project import (
    CreateProjectRequest,
    ProjectResponse,
    UpdateProjectRequest,
)
from app.services.auth_service import AuthService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_service(db: Session = Depends(get_db)) -> ProjectService:
    return ProjectService(db=db)


def get_auth_service(
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
) -> AuthService:
    return AuthService(db=db, redis_client=redis)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
async def create_project(
    request: Request,
    project_data: CreateProjectRequest,
    project_svc: ProjectService = Depends(get_project_service),
    auth: AuthService = Depends(get_auth_service),
    current_user: dict = Depends(RequireViewer),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    project = project_svc.create_project(
        owner_id=current_user.get("user_id"),
        name=project_data.name,
        description=project_data.description,
        ip=client_ip,
        user_agent=user_agent,
    )
    return ProjectResponse(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
    )


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List projects (ownership-filtered)",
)
async def list_projects(
    project_svc: ProjectService = Depends(get_project_service),
    current_user: dict = Depends(RequireViewer),
):
    projects = project_svc.list_projects(
        user_id=current_user.get("user_id"),
        user_role=current_user.get("role", "viewer"),
    )
    return [
        ProjectResponse(
            id=p.id,
            owner_id=p.owner_id,
            name=p.name,
            description=p.description,
            created_at=p.created_at,
        )
        for p in projects
    ]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get a project by ID (ownership-checked)",
)
async def get_project(
    project_id: str,
    project_svc: ProjectService = Depends(get_project_service),
    current_user: dict = Depends(RequireViewer),
):
    project = project_svc.get_project(
        project_id=project_id,
        user_id=current_user.get("user_id"),
        user_role=current_user.get("role", "viewer"),
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return ProjectResponse(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
    )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project (ownership-checked)",
)
async def update_project(
    request: Request,
    project_id: str,
    project_data: UpdateProjectRequest,
    project_svc: ProjectService = Depends(get_project_service),
    auth: AuthService = Depends(get_auth_service),
    current_user: dict = Depends(RequireViewer),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    project = project_svc.update_project(
        project_id=project_id,
        user_id=current_user.get("user_id"),
        user_role=current_user.get("role", "viewer"),
        name=project_data.name,
        description=project_data.description,
        ip=client_ip,
        user_agent=user_agent,
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return ProjectResponse(
        id=project.id,
        owner_id=project.owner_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
    )


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project (ownership-checked)",
)
async def delete_project(
    request: Request,
    project_id: str,
    project_svc: ProjectService = Depends(get_project_service),
    auth: AuthService = Depends(get_auth_service),
    current_user: dict = Depends(RequireViewer),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    success = project_svc.delete_project(
        project_id=project_id,
        user_id=current_user.get("user_id"),
        user_role=current_user.get("role", "viewer"),
        ip=client_ip,
        user_agent=user_agent,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
