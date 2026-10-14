"""Run isolated PostgreSQL 18 when Docker Desktop is unavailable. Local only; loopback binding."""

import subprocess
from pathlib import Path

import psycopg
from dotenv import dotenv_values
from psycopg import sql


def main():
    root = Path(__file__).resolve().parents[1]
    env = dotenv_values(root / ".env")
    binary = root / ".local/pgsql/bin"
    data = root / ".local/pgdata"
    password_file = root / ".local/.init-password"
    if not (data / "PG_VERSION").exists():
        password_file.write_text(env["POSTGRES_PASSWORD"])
        try:
            subprocess.run(
                [
                    str(binary / "initdb.exe"),
                    "-D",
                    str(data),
                    "-U",
                    "postgres",
                    "-A",
                    "scram-sha-256",
                    "--pwfile",
                    str(password_file),
                    "--encoding=UTF8",
                    "--locale=C",
                ],
                check=True,
            )
        finally:
            password_file.unlink(missing_ok=True)
    check = subprocess.run([str(binary / "pg_ctl.exe"), "-D", str(data), "status"], capture_output=True)
    if check.returncode:
        subprocess.run(
            [
                str(binary / "pg_ctl.exe"),
                "-D",
                str(data),
                "-l",
                str(root / ".local/postgres.log"),
                "-o",
                "-p 5440 -h 127.0.0.1",
                "-w",
                "start",
            ],
            check=True,
        )
    with psycopg.connect(
        host="127.0.0.1",
        port=5440,
        user="postgres",
        password=env["POSTGRES_PASSWORD"],
        dbname="postgres",
        autocommit=True,
    ) as conn:
        for role, key in [("gridsignal_writer", "WRITER_PASSWORD"), ("gridsignal_reader", "READER_PASSWORD")]:
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                conn.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                        sql.Identifier(role), sql.Literal(env[key])
                    )
                )
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname='gridsignal_db'").fetchone():
            conn.execute("CREATE DATABASE gridsignal_db")
        print(conn.execute("SELECT version()").fetchone()[0])
    print("Isolated PostgreSQL is ready at 127.0.0.1:5440; data remains in ignored .local/pgdata.")


if __name__ == "__main__":
    main()
