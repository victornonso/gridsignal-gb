from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    root = Path(__file__).resolve().parents[3]
    for filename in ["db/sql/core/schema.sql", "db/sql/marts/views.sql"]:
        op.get_bind().exec_driver_sql((root / filename).read_text())


def downgrade():
    for schema in ["mart", "core", "raw", "ops"]:
        op.execute(f"DROP SCHEMA {schema} CASCADE")
