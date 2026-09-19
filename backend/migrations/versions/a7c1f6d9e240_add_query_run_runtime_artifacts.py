"""Add safe runtime artifacts to query runs."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a7c1f6d9e240"
down_revision = "6f2b3a91c4de"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("query_runs", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("query_runs", sa.Column("result_json", postgresql.JSONB(), nullable=True))
    op.add_column(
        "query_runs",
        sa.Column(
            "trace_json",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "query_runs",
        sa.Column(
            "warnings",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.alter_column("query_runs", "trace_json", server_default=None)
    op.alter_column("query_runs", "warnings", server_default=None)


def downgrade() -> None:
    op.drop_column("query_runs", "warnings")
    op.drop_column("query_runs", "trace_json")
    op.drop_column("query_runs", "result_json")
    op.drop_column("query_runs", "error_message")
