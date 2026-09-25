import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path

def get_conn():
    db_path = os.environ.get("DB_PATH", "")
    if not db_path:
        raise RuntimeError("DB_PATH must be configured explicitly")
    path = Path(db_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


@contextmanager
def transaction():
    """Single-connection transactional block. Commits on success, rolls back on exception."""
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query(sql, params=(), one=False, conn=None):
    own = conn is None
    if own:
        conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        return (dict(rows[0]) if rows else None) if one else [dict(r) for r in rows]
    finally:
        if own:
            conn.close()


def execute(sql, params=(), conn=None):
    own = conn is None
    if own:
        conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        if own:
            conn.commit()
        return cur.lastrowid, cur.rowcount
    finally:
        if own:
            conn.close()


def executemany(sql, param_list, conn=None):
    own = conn is None
    if own:
        conn = get_conn()
    try:
        cur = conn.executemany(sql, param_list)
        if own:
            conn.commit()
        return cur.rowcount
    finally:
        if own:
            conn.close()


def now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_pagination(args, default_limit=200, max_limit=1000):
    # Clamp limit to [1, max_limit]. Negative LIMIT in SQLite means "no limit"
    # — must reject to prevent full-table dumps via ?limit=-1.
    try:
        limit = int(args.get("limit", default_limit))
    except (ValueError, TypeError):
        limit = default_limit
    limit = max(1, min(limit, max_limit))
    try:
        offset = int(args.get("offset", 0))
    except (ValueError, TypeError):
        offset = 0
    offset = max(0, offset)
    return limit, offset


def parse_int(value, default=None):
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default
