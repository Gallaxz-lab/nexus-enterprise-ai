from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from sqlalchemy import create_engine
from app.config import settings
from app.core.database.connection import Base
from app.core.database import models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_online() -> None:
    """Executes database migrations in online transactional mode."""
    # Force Alembic to draw directly from our encoded helper property
    connectable = create_engine(
        settings.encoded_database_url,
        poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

run_migrations_online()
