"""Backfill retained result snapshots into saved analyses."""

import sqlalchemy as sa
from alembic import op

revision = "a6c2d4e8f1b3"
down_revision = "f5b8c1d2e3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE saved_analyses AS saved
            SET result_json = runs.result_json
            FROM query_runs AS runs
            WHERE saved.source_query_run_id = runs.id
              AND saved.result_json IS NULL
              AND runs.result_json IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("UPDATE saved_analyses SET result_json = NULL"))
