"""VIXOR — Project service (T-017).

Project business logic with ownership enforcement.
"""

from sqlalchemy.orm import Session

from app.models.project import Project
from app.services.audit_service import write_audit_log


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def create_project(
        self,
        owner_id: str,
        name: str,
        description: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> Project:
        project = Project(
            owner_id=owner_id,
            name=name,
            description=description,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        write_audit_log(
            self.db,
            action="project_created",
            resource_type="project",
            resource_id=project.id,
            user_id=owner_id,
            ip=ip,
            user_agent=user_agent,
            metadata={"name": project.name},
        )
        return project

    def get_project(
        self, project_id: str, user_id: str, user_role: str
    ) -> Project | None:
        """Get a project by ID with ownership check.

        Admins can see all projects; others only see their own.
        Returns None if not found or not owned (for 404 response).
        """
        query = self.db.query(Project).filter(Project.id == project_id)
        if user_role != "admin":
            query = query.filter(Project.owner_id == user_id)
        return query.first()

    def list_projects(self, user_id: str, user_role: str) -> list[Project]:
        """List projects with ownership filtering.

        Admins see all projects; others see only their own.
        """
        query = self.db.query(Project)
        if user_role != "admin":
            query = query.filter(Project.owner_id == user_id)
        return query.all()

    def update_project(
        self,
        project_id: str,
        user_id: str,
        user_role: str,
        name: str | None = None,
        description: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> Project | None:
        project = self.get_project(project_id, user_id, user_role)
        if not project:
            return None

        updated_fields = {}
        if name is not None:
            updated_fields["name"] = {"old": project.name, "new": name}
            project.name = name
        if description is not None:
            updated_fields["description"] = {
                "old": project.description,
                "new": description,
            }
            project.description = description

        self.db.commit()
        self.db.refresh(project)

        if updated_fields:
            write_audit_log(
                self.db,
                action="project_updated",
                resource_type="project",
                resource_id=project.id,
                user_id=user_id,
                ip=ip,
                user_agent=user_agent,
                metadata=updated_fields,
            )
        return project

    def delete_project(
        self,
        project_id: str,
        user_id: str,
        user_role: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> bool:
        project = self.get_project(project_id, user_id, user_role)
        if not project:
            return False

        self.db.delete(project)
        self.db.commit()

        write_audit_log(
            self.db,
            action="project_deleted",
            resource_type="project",
            resource_id=project_id,
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
            metadata={"name": project.name},
        )
        return True
