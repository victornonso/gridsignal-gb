from alembic import context
from sqlalchemy import create_engine

from apps.api.app.config import settings

engine = create_engine(settings.migration_database_url)
with engine.connect() as connection:
    context.configure(connection=connection, transactional_ddl=True)
    with context.begin_transaction():
        context.run_migrations()
