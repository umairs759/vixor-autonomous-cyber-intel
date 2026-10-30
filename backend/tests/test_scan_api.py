"""Scan creation validation and Celery dispatch without a live broker."""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.api.v1.scans import create_scan
from app.models.asset import Asset, ScopeStatus
from app.models.domain import Domain, DomainStatus, VerificationMethod
from app.models.project import Project
from app.models.scan import Scan
from app.models.scan_asset import ScanAsset
from app.models.user import User, UserRole
from app.schemas.scan import ScanCreateRequest
from app.services.domain_service import DomainService


def _run_without_event_loop(coroutine):
    with pytest.raises(StopIteration) as result:
        coroutine.send(None)
    return result.value.value


def _owned_domain(db_session, verified=True):
    user = User(
        email=f"{uuid.uuid4()}@example.com",
        password_hash="test-hash",
        role=UserRole.analyst,
    )
    db_session.add(user)
    db_session.flush()
    project = Project(owner_id=user.id, name="Authorized project")
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
    db_session.flush()
    asset = Asset(
        domain_id=domain.id,
        hostname="app.example.test",
        scope_status=ScopeStatus.in_scope,
        is_live=True,
    )
    db_session.add(asset)
    db_session.commit()
    return user, domain, asset


def test_create_scan_validates_scope_and_dispatches(db_session, mocker):
    user, domain, asset = _owned_domain(db_session)
    mocker.patch("app.api.v1.scans.is_in_scope", return_value=(True, None))
    dispatch = mocker.patch("app.workers.tasks_scan.run_scan.delay")

    result = _run_without_event_loop(
        create_scan(
            ScanCreateRequest(domain_id=domain.id, asset_ids=[asset.id]),
            db_session,
            DomainService(db_session),
            {"user_id": user.id, "role": "analyst"},
        )
    )

    scan = db_session.query(Scan).filter_by(id=result["scan_id"]).one()
    association = db_session.query(ScanAsset).filter_by(scan_id=scan.id).one()
    assert result["status"] == "queued"
    assert association.asset_id == asset.id
    dispatch.assert_called_once_with(scan.id, domain.id, [asset.id])


def test_create_scan_rejects_unverified_domain(db_session, mocker):
    user, domain, asset = _owned_domain(db_session, verified=False)
    dispatch = mocker.patch("app.workers.tasks_scan.run_scan.delay")

    with pytest.raises(HTTPException) as error:
        _run_without_event_loop(
            create_scan(
                ScanCreateRequest(domain_id=domain.id, asset_ids=[asset.id]),
                db_session,
                DomainService(db_session),
                {"user_id": user.id, "role": "analyst"},
            )
        )

    assert error.value.status_code == 409
    dispatch.assert_not_called()


def test_create_scan_rejects_asset_from_another_domain(db_session, mocker):
    user, domain, _asset = _owned_domain(db_session)
    _, _, other_asset = _owned_domain(db_session)
    dispatch = mocker.patch("app.workers.tasks_scan.run_scan.delay")

    with pytest.raises(HTTPException) as error:
        _run_without_event_loop(
            create_scan(
                ScanCreateRequest(domain_id=domain.id, asset_ids=[other_asset.id]),
                db_session,
                DomainService(db_session),
                {"user_id": user.id, "role": "analyst"},
            )
        )

    assert error.value.status_code == 404
    dispatch.assert_not_called()
