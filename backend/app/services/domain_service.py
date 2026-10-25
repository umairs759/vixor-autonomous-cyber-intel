"""VIXOR — Domain service (T-018, T-019).

Domain registration with cryptographically random verification tokens,
and ownership enforcement.
"""

import secrets

from sqlalchemy.orm import Session

from app.models.domain import Domain, DomainStatus, VerificationMethod
from app.services.audit_service import write_audit_log


class DomainService:
    def __init__(self, db: Session):
        self.db = db

    def register_domain(
        self,
        project_id: str,
        user_id: str,
        root_domain: str,
        verification_method: str = "dns_txt",
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> Domain:
        """Register a new domain with a random verification token.

        Domain starts as UNVERIFIED. Scans are blocked until verified.
        """
        # Normalize domain to lowercase
        root_domain = root_domain.strip().lower()

        verification_token = secrets.token_urlsafe(32)

        # Validate verification method
        try:
            method = VerificationMethod(verification_method)
        except ValueError:
            method = VerificationMethod.dns_txt

        domain = Domain(
            project_id=project_id,
            root_domain=root_domain,
            verification_token=verification_token,
            verification_method=method,
            status=DomainStatus.unverified,
        )
        self.db.add(domain)
        self.db.commit()
        self.db.refresh(domain)

        write_audit_log(
            self.db,
            action="domain_registered",
            resource_type="domain",
            resource_id=domain.id,
            user_id=user_id,
            ip=ip,
            user_agent=user_agent,
            metadata={
                "root_domain": domain.root_domain,
                "verification_method": domain.verification_method.value,
            },
        )
        return domain

    def get_domain(
        self,
        domain_id: str,
        user_id: str,
        user_role: str,
    ) -> Domain | None:
        """Get a domain by ID with ownership check.

        Admins can see all domains; others only see domains in their projects.
        Returns None if not found or not accessible (404 for IDOR protection).
        """
        from app.models.project import Project

        query = (
            self.db.query(Domain)
            .join(Project, Domain.project_id == Project.id)
            .filter(Domain.id == domain_id)
        )

        if user_role != "admin":
            query = query.filter(Project.owner_id == user_id)

        return query.first()

    def list_domains(
        self,
        project_id: str,
        user_id: str,
        user_role: str,
    ) -> list[Domain]:
        """List domains for a project with ownership check."""
        from app.models.project import Project

        query = (
            self.db.query(Domain)
            .join(Project, Domain.project_id == Project.id)
            .filter(Domain.project_id == project_id)
        )

        if user_role != "admin":
            query = query.filter(Project.owner_id == user_id)

        return query.all()
