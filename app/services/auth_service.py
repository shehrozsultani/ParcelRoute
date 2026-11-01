import re

from werkzeug.security import check_password_hash, generate_password_hash

from .. import db

VALID_ROLES = {"admin", "ops"}
USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,64}$")


def init_auth_schema():
    sql = """
    CREATE TABLE IF NOT EXISTS auth_users (
        user_id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(64) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        role VARCHAR(16) NOT NULL,
        is_active TINYINT(1) NOT NULL DEFAULT 1,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    )
    """
    _execute_write(sql, ())


def hash_password(password):
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("Password must be at least 12 characters long.")
    return generate_password_hash(password)


def verify_password(password, password_hash):
    return bool(password_hash) and check_password_hash(password_hash, password)


def create_user(username, password, role):
    username = _normalize_username(username)
    role = _normalize_role(role)
    pwd_hash = hash_password(password)

    sql = """
    INSERT INTO auth_users (username, password_hash, role, is_active)
    VALUES (%s, %s, %s, 1)
    """
    _execute_write(sql, (username, pwd_hash, role))


def get_user_by_username(username):
    username = _normalize_username(username)
    sql = """
    SELECT user_id, username, password_hash, role, is_active
    FROM auth_users
    WHERE username = %s
    LIMIT 1
    """
    return _fetch_one(sql, (username,))


def get_user_by_id(user_id):
    sql = """
    SELECT user_id, username, role, is_active
    FROM auth_users
    WHERE user_id = %s
    LIMIT 1
    """
    return _fetch_one(sql, (user_id,))


def authenticate_user(username, password):
    user = get_user_by_username(username)
    if not user or not user.get("is_active"):
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "role": user["role"],
    }


def has_permission(role, permission):
    permissions = {
        "admin": {"admin:access", "ops:access"},
        "ops": {"ops:access"},
    }
    return permission in permissions.get(role, set())


def _normalize_username(username):
    if not isinstance(username, str):
        raise ValueError("Invalid username.")
    username = username.strip()
    if not USERNAME_RE.match(username):
        raise ValueError("Username must be 3-64 chars and use letters, numbers, _, -, .")
    return username


def _normalize_role(role):
    role = str(role).strip().lower()
    if role not in VALID_ROLES:
        raise ValueError("Role must be one of: admin, ops.")
    return role


def _fetch_one(sql, params):
    conn = None
    try:
        conn = db._connect()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    except Exception as exc:
        raise db.DatabaseError("Database query failed") from exc
    finally:
        if conn is not None:
            conn.close()


def _execute_write(sql, params):
    conn = None
    try:
        conn = db._connect()
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()
    except Exception as exc:
        if conn is not None:
            conn.rollback()
        raise db.DatabaseError("Database query failed") from exc
    finally:
        if conn is not None:
            conn.close()
