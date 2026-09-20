"""Add dashboard widget result snapshots and refresh status."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b8d2e41c730a"
down_revision = "a7c1f6d9e240"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dashboard_widgets",
        sa.Column("source_query_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("dashboard_widgets", sa.Column("result_json", postgresql.JSONB(), nullable=True))
    op.add_column(
        "dashboard_widgets",
        sa.Column("status", sa.String(length=24), server_default="ready", nullable=False),
    )
    op.add_column("dashboard_widgets", sa.Column("row_count", sa.BigInteger(), nullable=True))
    op.add_column("dashboard_widgets", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column(
        "dashboard_widgets",
        sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "dashboard_widgets", sa.Column("last_error_code", sa.String(length=80), nullable=True)
    )
    op.add_column("dashboard_widgets", sa.Column("last_error_message", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_dashboard_widgets_source_query_run_id",
        "dashboard_widgets",
        "query_runs",
        ["source_query_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_dashboard_widgets_status",
        "dashboard_widgets",
        "status IN ('ready', 'empty', 'stale', 'failed')",
    )
    op.alter_column("dashboard_widgets", "status", server_default=None)


def downgrade() -> None:
    op.drop_constraint("ck_dashboard_widgets_status", "dashboard_widgets", type_="check")
    op.drop_constraint(
        "fk_dashboard_widgets_source_query_run_id", "dashboard_widgets", type_="foreignkey"
    )
    for column in (
        "last_error_message",
        "last_error_code",
        "last_refreshed_at",
        "duration_ms",
        "row_count",
        "status",
        "result_json",
        "source_query_run_id",
    ):
        op.drop_column("dashboard_widgets", column)
