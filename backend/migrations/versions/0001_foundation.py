"""Establish pgvector availability; product tables belong to Phase 2."""

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # The extension may already exist or support other objects; retain it.
    pass
