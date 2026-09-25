"""Shared fixtures for API tests."""
import os
import sys
import tempfile
import sqlite3
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ["USER_TOKENS"] = "admin_user:testtoken,editor_user:editortoken"
os.environ["ADMIN_NAMES"] = "admin_user"

MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")
SCHEMA_PATH = os.path.join(MIGRATIONS_DIR, "001_initial.sql")


def _apply_sql_migrations(conn):
    """Apply 001_initial + any later *.sql migrations in order (skips .py seeders)."""
    files = sorted(f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql"))
    for fname in files:
        conn.executescript(open(os.path.join(MIGRATIONS_DIR, fname)).read())
    conn.execute("PRAGMA journal_mode=WAL")


@pytest.fixture(scope="session")
def db_file():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    os.environ["DB_PATH"] = path

    conn = sqlite3.connect(path)
    _apply_sql_migrations(conn)
    conn.execute("INSERT INTO publishers (name, domain, dr, market) VALUES ('TestPub','test.example.test',80,'IT')")
    conn.execute("INSERT INTO publishers (name, domain, dr, market) VALUES ('TestPubES','es.com',75,'ES')")
    conn.execute("INSERT INTO journalists (email, first_name, last_name, publisher_id, market) VALUES ('j1@example.test','Mario','Rossi',1,'IT')")
    conn.execute("INSERT INTO campaigns (name, market) VALUES ('TestCamp','IT')")
    conn.commit()
    conn.close()

    yield path

    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture(scope="session")
def client(db_file):
    import app as app_module
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


@pytest.fixture(scope="session")
def fuzz_db():
    previous_db_path = os.environ.get("DB_PATH")
    fd, path = tempfile.mkstemp(suffix="_fuzz.sqlite")
    os.close(fd)
    fuzz_db_path = path
    os.environ["DB_PATH"] = fuzz_db_path

    conn = sqlite3.connect(fuzz_db_path)
    _apply_sql_migrations(conn)
    conn.execute("INSERT INTO publishers (name, domain, dr, market) VALUES ('FuzzPub','fuzz.example.test',60,'IT')")
    conn.execute("INSERT INTO journalists (email, first_name, market) VALUES ('fuzz@example.test','Fuzz','IT')")
    conn.commit()
    conn.close()

    yield fuzz_db_path

    try:
        os.unlink(fuzz_db_path)
    except OSError:
        pass
    if previous_db_path is None:
        os.environ.pop("DB_PATH", None)
    else:
        os.environ["DB_PATH"] = previous_db_path


@pytest.fixture(scope="session")
def fuzz_client(fuzz_db):
    import importlib
    import app as app_module
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c
