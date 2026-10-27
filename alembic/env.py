from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.models import Base
from app.config import settings


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


alembic_database_url ='sqlite+aiosqlite:///test.db'


# alembic_database_url = (
#     f'postgresql+psycopg://'
#     f'{settings.POSTGRES_USER}:'
#     f'{settings.POSTGRES_PASSWORD}@'
#     f'{settings.POSTGRES_HOST}:'
#     f'{settings.POSTGRES_PORT}/'
#     f'{settings.POSTGRES_DB}'
# )

config.set_main_option(
    'sqlalchemy.url',
    alembic_database_url,
)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    # Создаем синхронный движок ТОЛЬКО для миграций
    # Драйвер pysqlite - это стандартный драйвер SQLite, он синхронный
    sync_url = "sqlite:///test.db" 
    
    connectable = engine_from_config(
        {"sqlalchemy.url": sync_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool, # Для SQLite лучше отключать пул в миграциях
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


# def run_migrations_online() -> None:
#     """Run migrations in 'online' mode.

#     In this scenario we need to create an Engine
#     and associate a connection with the context.

#     """
#     connectable = engine_from_config(
#         config.get_section(config.config_ini_section, {}),
#         prefix='sqlalchemy.',
#         poolclass=pool.NullPool,
#     )

#     with connectable.connect() as connection:
#         context.configure(
#             connection=connection,
#             target_metadata=target_metadata,
#         )

#         with context.begin_transaction():
#             context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
