import os
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from apps.api.app.config import settings


@pytest.fixture(scope="session")
def isolated_database():
    if os.getenv("RUN_DB_TESTS") != "1":
        pytest.skip("Database tests disabled")
    name = "gridsignal_test_" + uuid4().hex[:12]
    admin_url = make_url(settings.migration_database_url)
    admin = create_engine(admin_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.exec_driver_sql(f"CREATE DATABASE {name}")
    migration_url = admin_url.set(database=name).render_as_string(hide_password=False)
    env = dict(os.environ, MIGRATION_DATABASE_URL=migration_url)
    root = Path(__file__).resolve().parents[2]
    subprocess.run(
        [
            str(root / ".venv/Scripts/python.exe") if os.name == "nt" else "python",
            "-m",
            "alembic",
            "upgrade",
            "head",
        ],
        env=env,
        cwd=root,
        check=True,
    )
    try:
        yield {
            "migration": migration_url,
            "writer": make_url(settings.database_url)
            .set(database=name)
            .render_as_string(hide_password=False),
            "reader": make_url(settings.read_database_url)
            .set(database=name)
            .render_as_string(hide_password=False),
        }
    finally:
        with admin.connect() as conn:
            conn.exec_driver_sql(f"DROP DATABASE {name} WITH (FORCE)")
        admin.dispose()
