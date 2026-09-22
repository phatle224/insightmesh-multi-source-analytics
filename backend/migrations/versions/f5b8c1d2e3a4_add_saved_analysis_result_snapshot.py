"""Persist result snapshots for saved analyses."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f5b8c1d2e3a4"
down_revision = "e1b4c7d9f012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "saved_analyses",
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("saved_analyses", "result_json")
