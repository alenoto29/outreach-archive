#!/usr/bin/env python3
"""Initialize an empty local database from the checked-in SQL migrations."""
import argparse
import sqlite3
from pathlib import Path


def initialize(path: Path) -> None:
    path = path.expanduser().resolve()
    if path.exists() and path.stat().st_size:
        raise SystemExit(f"refusing to initialize a non-empty file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    migrations = Path(__file__).resolve().parents[1] / "migrations"
    connection = sqlite3.connect(path)
    try:
        for migration in sorted(migrations.glob("*.sql")):
            connection.executescript(migration.read_text(encoding="utf-8"))
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.commit()
        version = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        print(f"Initialized empty database at {path} (schema {version})")
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path, help="new database file path")
    args = parser.parse_args()
    initialize(args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
