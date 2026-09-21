"""Add immutable semantic manifest snapshots."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c9f31a2e7d44"
down_revision = "b8d2e41c730a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "semantic_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("datasource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata_hash", sa.String(length=64), nullable=False),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column("configuration_json", postgresql.JSONB(), nullable=False),
        sa.Column("manifest_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("version > 0", name="ck_semantic_manifests_version"),
        sa.ForeignKeyConstraint(
            ["datasource_id"], ["datasources.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "datasource_id", "manifest_hash", name="uq_semantic_manifests_datasource_hash"
        ),
        sa.UniqueConstraint(
            "datasource_id", "version", name="uq_semantic_manifests_datasource_version"
        ),
    )
    op.create_index(
        "ix_semantic_manifests_datasource_created",
        "semantic_manifests",
        ["datasource_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_semantic_manifests_datasource_created", table_name="semantic_manifests")
    op.drop_table("semantic_manifests")
