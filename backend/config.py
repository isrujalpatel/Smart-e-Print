import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Flask ───────────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

    # ── Database (Supabase PostgreSQL) ──────────────────────────────────────────
    # Supabase sometimes returns 'postgres://' — SQLAlchemy needs 'postgresql://'
    _db_url = os.getenv("DATABASE_URL", "")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    # Fallback to SQLite for local development when DATABASE_URL is not set
    SQLALCHEMY_DATABASE_URI = _db_url or "sqlite:///smart_eprint.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Connection pooling only for PostgreSQL (not compatible with SQLite)
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"pool_pre_ping": True, "pool_recycle": 300}
        if SQLALCHEMY_DATABASE_URI.startswith("postgresql")
        else {}
    )

    # ── JWT ─────────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
