from __future__ import annotations

import hashlib
import os
from pathlib import Path

from sqlalchemy import text

from .db import engine


def migration_directory() -> Path:
    configured = os.getenv("MIGRATIONS_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[2] / "migrations"


def apply_migrations() -> None:
    directory = migration_directory()
    migrations = sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
    if not migrations:
        raise RuntimeError(f"No SQL migrations found in {directory}")

    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtext('study_for_job_schema_migrations'))"))
        connection.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              checksum CHAR(64) NOT NULL,
              applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        applied = dict(connection.execute(text("SELECT version, checksum FROM schema_migrations")).all())

        for migration in migrations:
            sql = migration.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
            recorded = applied.get(migration.name)
            if recorded and recorded != checksum:
                raise RuntimeError(f"Applied migration changed: {migration.name}")
            if recorded:
                continue
            connection.exec_driver_sql(sql)
            connection.execute(
                text("INSERT INTO schema_migrations (version, checksum) VALUES (:version, :checksum)"),
                {"version": migration.name, "checksum": checksum},
            )


if __name__ == "__main__":
    apply_migrations()
