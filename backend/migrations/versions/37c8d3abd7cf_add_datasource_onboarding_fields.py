import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "37c8d3abd7cf"
down_revision = "963b9a2f25ea"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "datasources",
        sa.Column("ssl_mode", sa.String(length=16), server_default="prefer", nullable=False),
    )
    op.add_column(
        "datasources",
        sa.Column(
            "allowed_schemas",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[\"public\"]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "datasources", sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("datasources", sa.Column("last_error_code", sa.String(length=80), nullable=True))
    op.create_check_constraint(
        op.f("ck_datasources_ssl_mode"),
        "datasources",
        "ssl_mode IN ('disable', 'prefer', 'require', 'verify-ca', 'verify-full')",
    )
    op.alter_column("datasources", "ssl_mode", server_default=None)
    op.alter_column("datasources", "allowed_schemas", server_default=None)


def downgrade() -> None:
    op.drop_constraint(op.f("ck_datasources_ssl_mode"), "datasources", type_="check")
    op.drop_column("datasources", "last_error_code")
    op.drop_column("datasources", "last_refreshed_at")
    op.drop_column("datasources", "allowed_schemas")
    op.drop_column("datasources", "ssl_mode")
