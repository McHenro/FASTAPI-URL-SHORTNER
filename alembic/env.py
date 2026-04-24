import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool  # builds a sync DB engine from config
from alembic import context                       # Alembic's runtime: knows DB state and migration history
from dotenv import load_dotenv

# Make .env variables (DATABASE_URL etc.) available via os.getenv()
load_dotenv()

# Parsed representation of alembic.ini (also called the config object)
config = context.config

# Our app uses asyncpg (async driver), but Alembic is a sync CLI tool — they don't mix.
# Swap +asyncpg → +psycopg2 for migrations only. The .env file stays unchanged.
db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "+psycopg2")
config.set_main_option("sqlalchemy.url", db_url)

# Activate the logging rules defined in alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base + every model module so they register their tables on Base.metadata.
# Without these imports, Alembic cannot see the tables during autogenerate.
from app.core.database import Base
from app.models import url  # noqa

# "What your Python models say the DB should look like" — Alembic diffs this against the live DB
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generates raw SQL without connecting to the DB (alembic upgrade --sql).
    Useful for reviewing or handing off SQL to a DBA."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connects to the live DB and applies pending migrations (alembic upgrade head)."""
    # Reads sqlalchemy.url from the [alembic] section and builds a sync engine
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # no connection pooling needed for a CLI tool
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


# Entry point: offline mode is triggered by the --sql flag, otherwise run online
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
