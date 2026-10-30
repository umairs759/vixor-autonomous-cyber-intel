"""Project API authentication, role, and ownership checks (T-017)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.config import get_settings
from app.core.security import create_access_token
from app.models.base import Base
from app.models.project import Project


@pytest.fixture(autouse=True)
def clean_projects(db_session):
    engine = create_engine(get_settings().DATABASE_URL)
    Base.metadata.create_all(engine)
    db_session.query(Project).delete()
    db_session.commit()
    engine.dispose()


def _headers(role: str, user_id: str) -> dict[str, str]:
    token = create_access_token(user_id, role, str(uuid.uuid4()))
    return {"Authorization": f"Bearer {token}"}


def _project(db_session, owner_id: str, name: str) -> Project:
    project = Project(owner_id=owner_id, name=name)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


def test_list_projects_requires_authentication(client: TestClient):
    assert client.get("/api/v1/projects").status_code == 401


@pytest.mark.parametrize("role", ["viewer", "analyst"])
def test_list_projects_filters_to_authenticated_owner(client, db_session, role):
    owner_id, other_id = str(uuid.uuid4()), str(uuid.uuid4())
    own = _project(db_session, owner_id, "Own project")
    _project(db_session, other_id, "Other project")

    response = client.get("/api/v1/projects", headers=_headers(role, owner_id))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [own.id]


def test_admin_can_list_all_projects(client, db_session):
    _project(db_session, str(uuid.uuid4()), "First")
    _project(db_session, str(uuid.uuid4()), "Second")

    response = client.get(
        "/api/v1/projects", headers=_headers("admin", str(uuid.uuid4()))
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_viewer_cannot_create_project(client: TestClient):
    response = client.post(
        "/api/v1/projects",
        headers=_headers("viewer", str(uuid.uuid4())),
        json={"name": "Read only"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["analyst", "admin"])
def test_analyst_and_admin_can_create_owned_project(client, role):
    user_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/projects",
        headers=_headers(role, user_id),
        json={"name": "Owned project"},
    )

    assert response.status_code == 201
    assert response.json()["owner_id"] == user_id


def test_user_cannot_read_another_users_project(client, db_session):
    project = _project(db_session, str(uuid.uuid4()), "Private")
    response = client.get(
        f"/api/v1/projects/{project.id}",
        headers=_headers("analyst", str(uuid.uuid4())),
    )
    assert response.status_code == 404
