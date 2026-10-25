"""Alembic environment config for VIXOR.

Uses the application SQLAlchemy metadata and DATABASE_URL from settings.
Runs migrations in online mode by default.
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.models.base import Base  # noqa: E402

# Import all models so they are registered on Base.metadata
import app.models.user  # noqa: F401
import app.models.audit_log  # noqa: F401
import app.models.project  # noqa: F401
import app.models.domain  # noqa: F401
import app.models.asset  # noqa: F401
import app.models.scan  # noqa: F401
import app.models.scan_asset  # noqa: F401
import app.models.finding  # noqa: F401
import app.models.finding_score  # noqa: F401
import app.models.finding_history  # noqa: F401
import app.models.correlation  # noqa: F401
import app.models.report  # noqa: F401
import app.models.schedule  # noqa: F401

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the SQLAlchemy URL from application settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
