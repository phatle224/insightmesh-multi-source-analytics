"""Add profiling refresh and semantic-index status fields."""

import sqlalchemy as sa
from alembic import op

revision = "6f2b3a91c4de"
down_revision = "37c8d3abd7cf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("datasources", sa.Column("profile_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "datasources",
        sa.Column(
            "semantic_status",
            sa.String(length=32),
            server_default="not_configured",
            nullable=False,
        ),
    )
    op.add_column(
        "datasources", sa.Column("semantic_error_code", sa.String(length=80), nullable=True)
    )
    op.create_unique_constraint(
        "uq_profile_statistics_field_id", "profile_statistics", ["field_id"]
    )
    op.alter_column("datasources", "semantic_status", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "uq_profile_statistics_field_id", "profile_statistics", type_="unique"
    )
    op.drop_column("datasources", "semantic_error_code")
    op.drop_column("datasources", "semantic_status")
    op.drop_column("datasources", "profile_hash")
