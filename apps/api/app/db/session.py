from sqlalchemy import create_engine

from apps.api.app.config import settings

read_engine = create_engine(
    settings.read_database_url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    connect_args={"options": "-c statement_timeout=15000 -c default_transaction_read_only=on"},
)
