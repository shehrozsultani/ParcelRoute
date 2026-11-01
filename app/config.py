"""Configuration, read from environment variables (.env). No secrets in code."""
import os
from datetime import timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv optional
    pass


class Config:
    APP_ENV = os.environ.get("APP_ENV", "production").strip().lower()
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = APP_ENV == "production"
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.environ.get("SESSION_LIFETIME_MINUTES", "60"))
    )

    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.environ.get("DB_PORT", "3306"))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_NAME = os.environ.get("DB_NAME", "project")
    # DB_SSL_MODE: disabled (local MySQL), required (Aiven/hosted MySQL with SSL)
    DB_SSL_MODE = os.environ.get("DB_SSL_MODE", "disabled").strip().lower()
    # Use ONE of these when SSL is required
    DB_SSL_CA_PATH = os.environ.get("DB_SSL_CA_PATH", "").strip()
    DB_SSL_CA_PEM = os.environ.get("DB_SSL_CA_PEM", "").strip()
    DB_SSL_CA_BASE64 = os.environ.get("DB_SSL_CA_BASE64", "").strip()
