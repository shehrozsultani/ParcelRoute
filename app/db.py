"""Database access layer. The ONLY place that talks to MySQL.

All queries use parameterized placeholders (%s) so user input is never
concatenated into SQL.
"""
from flask import current_app, g


class DatabaseError(Exception):
    """Raised when MySQL is unreachable or a query fails."""


def _ssl_options(cfg):
    import base64
    import os

    mode = str(cfg.get("DB_SSL_MODE", "disabled")).strip().lower()
    if mode in {"", "0", "false", "off", "disable", "disabled", "none"}:
        return None

    ca_path = str(cfg.get("DB_SSL_CA_PATH", "")).strip()
    if ca_path:
        if not os.path.exists(ca_path):
            raise ValueError(f"DB_SSL_CA_PATH does not exist: {ca_path}")
        return {"ca": ca_path}

    ca_pem = str(cfg.get("DB_SSL_CA_PEM", "")).strip()
    if ca_pem:
        ca_file = "/tmp/nodetonest-db-ca.pem"
        with open(ca_file, "w", encoding="utf-8") as f:
            f.write(ca_pem)
        return {"ca": ca_file}

    ca_b64 = str(cfg.get("DB_SSL_CA_BASE64", "")).strip()
    if ca_b64:
        try:
            ca_pem = base64.b64decode(ca_b64, validate=True)
        except Exception as exc:
            raise ValueError("DB_SSL_CA_BASE64 is not valid base64") from exc
        ca_file = "/tmp/nodetonest-db-ca.pem"
        with open(ca_file, "wb") as f:
            f.write(ca_pem)
        return {"ca": ca_file}

    raise ValueError(
        "DB_SSL_MODE is enabled but no CA was provided. Set DB_SSL_CA_PATH, DB_SSL_CA_PEM, or DB_SSL_CA_BASE64."
    )


def _connect():
    import pymysql

    cfg = current_app.config
    connect_kwargs = dict(
        host=cfg["DB_HOST"],
        port=cfg["DB_PORT"],
        user=cfg["DB_USER"],
        passwd=cfg["DB_PASSWORD"],
        database=cfg["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )

    ssl_opts = _ssl_options(cfg)
    if ssl_opts:
        connect_kwargs["ssl"] = ssl_opts

    return pymysql.connect(**connect_kwargs)


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
