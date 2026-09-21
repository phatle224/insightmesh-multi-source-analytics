"""Add query-run provider call observability."""

import sqlalchemy as sa
from alembic import op

revision = "d4a71f93c820"
down_revision = "c9f31a2e7d44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "query_runs",
        sa.Column(
            "provider_call_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_query_runs_provider_call_count",
        "query_runs",
        "provider_call_count >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_query_runs_provider_call_count",
        "query_runs",
        type_="check",
    )
    op.drop_column("query_runs", "provider_call_count")
