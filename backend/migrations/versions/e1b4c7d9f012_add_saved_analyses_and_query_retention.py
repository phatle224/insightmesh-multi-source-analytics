"""Add durable saved analyses and expiry timestamps for query runs."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e1b4c7d9f012"
down_revision = "d4a71f93c820"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "query_runs",
        sa.Column("artifacts_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "query_runs",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE query_runs
            SET artifacts_expires_at = created_at + interval '7 days',
                expires_at = created_at + interval '90 days'
            WHERE artifacts_expires_at IS NULL OR expires_at IS NULL
            """
        )
    )
    op.create_index(
        "ix_query_runs_artifacts_expires_at",
        "query_runs",
        ["artifacts_expires_at"],
        postgresql_where=sa.text("result_json IS NOT NULL OR trace_json <> '[]'::jsonb"),
    )
    op.create_index("ix_query_runs_expires_at", "query_runs", ["expires_at"])
    op.create_index(
        "ix_query_runs_datasource_created",
        "query_runs",
        ["datasource_id", "created_at", "id"],
    )
    op.create_table(
        "saved_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("datasource_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("validated_query", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("query_type", sa.String(length=24), nullable=False),
        sa.Column("visualization_type", sa.String(length=40), nullable=True),
        sa.Column(
            "tags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("source_query_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["datasource_id"],
            ["datasources.id"],
            ondelete="CASCADE",
            name="fk_saved_analyses_datasource_id_datasources",
        ),
        sa.ForeignKeyConstraint(
            ["source_query_run_id"],
            ["query_runs.id"],
            ondelete="SET NULL",
            name="fk_saved_analyses_source_query_run_id_query_runs",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_saved_analyses"),
    )
    op.create_index(
        "ix_saved_analyses_datasource_updated",
        "saved_analyses",
        ["datasource_id", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_saved_analyses_datasource_updated", table_name="saved_analyses")
    op.drop_table("saved_analyses")
    op.drop_index("ix_query_runs_datasource_created", table_name="query_runs")
    op.drop_index("ix_query_runs_expires_at", table_name="query_runs")
    op.drop_index("ix_query_runs_artifacts_expires_at", table_name="query_runs")
    op.drop_column("query_runs", "expires_at")
    op.drop_column("query_runs", "artifacts_expires_at")
