from alembic import context
from sqlalchemy import create_engine

from api.settings import get_settings
from persistence import models  # noqa: F401
from persistence.base import Base

engine = create_engine(get_settings().database_url, connect_args={"connect_timeout": 5})
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
