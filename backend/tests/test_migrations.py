"""Tests that Alembic migrations apply and roll back cleanly (T-014).

Uses an in-memory SQLite database. SQLite does not support all PostgreSQL
features (JSONB, native ENUM), so these tests verify migration structure
and application order rather than full PostgreSQL semantics.

Alembic commands are invoked via subprocess to avoid import shadowing
between our backend/alembic/ package directory and the installed alembic
package.
"""

import os
import subprocess
import sys
import tempfile

from sqlalchemy import create_engine, inspect

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app.models.asset
import app.models.audit_log
import app.models.correlation
import app.models.domain
import app.models.finding
import app.models.finding_history
import app.models.finding_score
import app.models.project
import app.models.report
import app.models.scan
import app.models.scan_asset
import app.models.schedule

# Import all model modules so they register on Base.metadata
import app.models.user  # noqa: F401
from app.models.base import Base

# Project root (parent of backend/) so the installed alembic package is used
# instead of the local backend/alembic/ package directory shadowing it.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _run_alembic(database_url: str, *args: str) -> subprocess.CompletedProcess:
    """Run an alembic CLI command with the given database URL.

    The subprocess is executed from the project root so that the local
    ``backend/alembic/`` package directory does not shadow the installed
    ``alembic`` package (which would raise ``No module named alembic.__main__``).
    From the project root, ``script_location = backend/alembic`` in
    ``backend/alembic.ini`` resolves correctly relative to the CWD.
    """
    env = dict(os.environ)
    env["DATABASE_URL"] = database_url
    env.setdefault(
        "JWT_SECRET_KEY", "test_jwt_secret_key_for_migration_tests_0123456789"
    )
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        cwd=_PROJECT_ROOT,
    )


def test_migrations_apply_and_rollback():
    """Migrations apply head -> then roll back to base cleanly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_migrations.db")
        database_url = f"sqlite:///{db_path}"

        # Apply all migrations to head
        result = _run_alembic(database_url, "upgrade", "head")
        assert result.returncode == 0, f"Alembic upgrade failed:\n{result.stderr}"

        # Verify expected tables exist
        engine = create_engine(database_url)
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        expected = {
            "users",
            "audit_logs",
            "projects",
            "domains",
            "assets",
            "scans",
            "scan_assets",
            "findings",
            "finding_scores",
            "finding_history",
            "correlations",
            "reports",
            "scan_schedules",
            "alembic_version",
        }
        missing = expected - table_names
        assert not missing, f"Missing tables after migration: {missing}"

        # Verify key columns exist
        columns = {c["name"] for c in inspector.get_columns("users")}
        assert {"id", "email", "password_hash", "role", "is_active"} <= columns

        columns = {c["name"] for c in inspector.get_columns("domains")}
        assert {"id", "project_id", "root_domain", "status"} <= columns

        columns = {c["name"] for c in inspector.get_columns("findings")}
        assert {"id", "fingerprint", "source_tool"} <= columns

        # Roll back to base
        result = _run_alembic(database_url, "downgrade", "base")
        assert result.returncode == 0, f"Alembic downgrade failed:\n{result.stderr}"

        # After downgrade to base, only alembic_version should remain
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        app_tables = table_names - {"alembic_version"}
        assert not app_tables, f"Tables remain after downgrade: {app_tables}"

        # Dispose engine to release SQLite file handle before cleanup
        engine.dispose()


def test_metadata_matches_tables():
    """SQLAlchemy Base metadata defines all expected tables."""
    expected = {
        "users",
        "audit_logs",
        "projects",
        "domains",
        "assets",
        "scans",
        "scan_assets",
        "findings",
        "finding_scores",
        "finding_history",
        "correlations",
        "reports",
        "scan_schedules",
    }
    defined = set(Base.metadata.tables.keys())
    missing = expected - defined
    assert not missing, f"Models missing from metadata: {missing}"
