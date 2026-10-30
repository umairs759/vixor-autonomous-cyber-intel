"""Discovery API authorization and queued-task behavior."""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.api.v1.discovery import discover_domain
from app.models.domain import Domain, DomainStatus, VerificationMethod
from app.models.project import Project
from app.models.user import User, UserRole
from app.services.domain_service import DomainService


def _run_without_event_loop(coroutine):
    with pytest.raises(StopIteration) as result:
        coroutine.send(None)
    return result.value.value


def _domain(db_session, verified=True):
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        password_hash="test-hash",
        role=UserRole.analyst,
    )
    db_session.add(user)
    db_session.flush()
    project = Project(owner_id=user.id, name="Discovery project")
    db_session.add(project)
    db_session.flush()
    domain = Domain(
        project_id=project.id,
        root_domain="example.test",
        verification_token="test-token",
        verification_method=VerificationMethod.dns_txt,
        status=DomainStatus.verified if verified else DomainStatus.unverified,
        verified_at=datetime.now(UTC) if verified else None,
    )
    db_session.add(domain)
    db_session.commit()
    return user, domain


def test_discovery_requires_verified_domain_and_dispatches(db_session, mocker):
    user, domain = _domain(db_session)
    mocker.patch("app.api.v1.discovery.is_in_scope", return_value=(True, None))
    dispatch = mocker.patch("app.workers.tasks_discovery.run_discovery.delay")

    result = _run_without_event_loop(
        discover_domain(
            domain.id,
            DomainService(db_session),
            {"user_id": user.id, "role": "analyst"},
        )
    )

    assert result == {"domain_id": domain.id, "status": "queued"}
    dispatch.assert_called_once_with(domain.id)


def test_discovery_rejects_unverified_domain(db_session, mocker):
    user, domain = _domain(db_session, verified=False)
    dispatch = mocker.patch("app.workers.tasks_discovery.run_discovery.delay")

    with pytest.raises(HTTPException) as error:
        _run_without_event_loop(
            discover_domain(
                domain.id,
                DomainService(db_session),
                {"user_id": user.id, "role": "analyst"},
            )
        )

    assert error.value.status_code == 409
    dispatch.assert_not_called()
