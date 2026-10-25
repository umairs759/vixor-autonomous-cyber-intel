"""Tests that Alembic migrations apply and roll back cleanly (T-014).

Uses an in-memory SQLite database. SQLite does not support all PostgreSQL
features (JSONB, native ENUM), so these tests verify migration structure
and application order rather than full PostgreSQL semantics.
"""

import os
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.base import Base  # noqa: E402


def _alembic_cfg() -> Config:
    cfg = Config("backend/alembic.ini")
    cfg.set_main_option("script_location", "backend/alembic")
    return cfg


def test_migrations_apply_and_rollback(tmp_path):
    """Migrations apply head -> then roll back to base cleanly."""
    db_path = tmp_path / "test_migrations.db"
    engine = create_engine(f"sqlite:///{db_path}")

    cfg = _alembic_cfg()
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    # Apply all migrations to head
    command.upgrade(cfg, "head")

    # Verify expected tables exist
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    expected = {
        "users", "audit_logs", "projects", "domains",
        "assets", "scans", "scan_assets", "findings",
        "finding_scores", "finding_history", "correlations",
        "reports", "scan_schedules", "alembic_version",
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
    command.downgrade(cfg, "base")

    # After downgrade to base, only alembic_version should remain
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    app_tables = table_names - {"alembic_version"}
    assert not app_tables, f"Tables remain after downgrade: {app_tables}"


def test_metadata_matches_tables(tmp_path):
    """SQLAlchemy Base metadata defines all expected tables."""
    expected = {
        "users", "audit_logs", "projects", "domains",
        "assets", "scans", "scan_assets", "findings",
        "finding_scores", "finding_history", "correlations",
        "reports", "scan_schedules",
    }
    defined = set(Base.metadata.tables.keys())
    missing = expected - defined
    assert not missing, f"Models missing from metadata: {missing}"
