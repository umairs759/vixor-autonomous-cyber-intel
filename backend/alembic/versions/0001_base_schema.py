"""Base schema

Revision ID: 0001_base_schema
Revises:
Create Date: 2026-10-25 00:00:00.000000

Base migration establishing the VIXOR database schema. Tables are added
incrementally in subsequent migrations (0002_users, 0003_projects_domains,
etc.). This revision creates the alembic_version table and is a no-op
for application tables.

"""

# revision identifiers, used by Alembic.
revision = "0001_base_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Base revision: no application tables yet.
    # Tables are created in T-011 to T-013 migrations.
    pass


def downgrade() -> None:
    pass
