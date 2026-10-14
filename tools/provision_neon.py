"""Provision the selected Neon project; keep credentials in ignored local storage."""

import argparse
import json
import os
import re
import secrets
import subprocess
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from psycopg import sql


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--profile", default="gridsignal-deploy")
    parser.add_argument("--org-id", required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = root / ".local" / "hosted.json"
    result = subprocess.run(
        ["npx.cmd", "--offline", "--yes", "neonctl@latest", "connection-string", "production",
         "--project-id", args.project_id, "--database-name", "gridsignal_db",
         "--role-name", "gridsignal_db_owner",
         "--profile", args.profile, "--org-id", args.org_id, "--output", "json"],
        capture_output=True, text=True, timeout=90, check=True,
    )
    output = result.stdout.strip()
    data = output if output.startswith(("postgres://", "postgresql://")) else json.loads(output)
    owner = data if isinstance(data, str) else data.get("uri", data.get("connection_string"))
    if not owner:
        raise RuntimeError("Unexpected CLI connection-string shape; no credentials printed")
    parts = urlsplit(owner)
    if parts.path != "/gridsignal_db":
        raise RuntimeError("Refusing to provision an unexpected database")
    if target.exists():
        config = json.loads(target.read_text())
        if config["project_id"] != args.project_id:
            raise RuntimeError("Hosted configuration belongs to another project")
    else:
        config = {"project_id": args.project_id, "passwords": {
            name: secrets.token_urlsafe(32) for name in ["gridsignal_reader", "gridsignal_writer"]
        }}
    with psycopg.connect(owner) as conn:
        for role, password in config["passwords"].items():
            exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone()
            if not exists:
                conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(password)))
            conn.execute(sql.SQL("GRANT CONNECT ON DATABASE gridsignal_db TO {}").format(sql.Identifier(role)))
        version = conn.execute("SHOW server_version").fetchone()[0]
        raw_oid = conn.execute("SELECT 'raw.api_response'::regclass::oid").fetchone()[0] if target.exists() else None
    config["migration_database_url"] = owner.replace("postgresql://", "postgresql+psycopg://", 1)
    for role, key in [("gridsignal_reader", "read_database_url"), ("gridsignal_writer", "database_url")]:
        auth = f"{role}:{quote(config['passwords'][role], safe='')}@{parts.netloc.split('@', 1)[1]}"
        config[key] = urlunsplit(("postgresql+psycopg", auth, parts.path, parts.query, parts.fragment))
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(config), encoding="utf-8")
    env = dict(os.environ, MIGRATION_DATABASE_URL=config["migration_database_url"])
    migration = subprocess.run([str(root / ".venv/Scripts/alembic.exe"), "upgrade", "head"],
                               cwd=root, env=env, capture_output=True, text=True, timeout=120)
    if migration.returncode:
        (target.parent / "hosted-migration.log").write_text(migration.stderr)
        raise RuntimeError("Hosted migration failed; diagnostic saved locally")
    if raw_oid is None:
        with psycopg.connect(owner) as conn:
            raw_oid = conn.execute("SELECT 'raw.api_response'::regclass::oid").fetchone()[0]
    for key in ["read_database_url", "database_url"]:
        with psycopg.connect(config[key].replace("postgresql+psycopg://", "postgresql://", 1)) as conn:
            if key == "read_database_url":
                assert not conn.execute("SELECT has_schema_privilege(current_user,'raw','USAGE')").fetchone()[0]
                assert not conn.execute("SELECT has_table_privilege(current_user,%s,'SELECT')", (raw_oid,)).fetchone()[0]
                assert not conn.execute("SELECT has_table_privilege(current_user,'core.carbon_observation','INSERT')").fetchone()[0]
            conn.execute("SELECT count(*) FROM core.carbon_observation").fetchone()
    print(json.dumps({"project": args.project_id, "postgres": version, "migration": "head",
                      "reader_isolation": "verified", "credentials": "saved in ignored .local/hosted.json"}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("Hosted provisioning stopped:", type(error).__name__)
        if isinstance(error, psycopg.errors.InsufficientPrivilege):
            print(error.diag.message_primary)
        if isinstance(error, subprocess.CalledProcessError):
            diagnostic = re.sub(r"(?:postgres(?:ql)?://|https?://)\S+", "[redacted URL]", error.stderr or "")
            print(diagnostic[:1500])
        raise SystemExit(1) from None
