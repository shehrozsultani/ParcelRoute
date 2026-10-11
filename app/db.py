"""Database access layer. The ONLY place that talks to MySQL.

All queries use parameterized placeholders (%s) so user input is never
concatenated into SQL.
"""
from flask import current_app, g


class DatabaseError(Exception):
    """Raised when MySQL is unreachable or a query fails."""



def _connect():
    import os
    import pymysql

    cfg = current_app.config
    ca_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "certs",
        "ca.pem",
    )

    return pymysql.connect(
        host=cfg["DB_HOST"],
        port=cfg["DB_PORT"],
        user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"],
        database=cfg["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
        ssl={"ca": ca_path},
    )



def _run(sql, params=()):
    """Execute a SELECT and return a list of dict rows."""
    try:
        if "conn" not in g:
            g.conn = _connect()
        with g.conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())
    except Exception as exc:
      print(f"DATABASE ERROR: {exc!r}", flush=True)
      raise DatabaseError(str(exc)) from exc


def query_all(sql, params=()):
    return _run(sql, params)


def query_one(sql, params=()):
    rows = _run(sql, params)
    return rows[0] if rows else None


def close_db(_exc=None):
    conn = g.pop("conn", None)
    if conn is not None:
        conn.close()
