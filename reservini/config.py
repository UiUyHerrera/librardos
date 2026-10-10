import os


def database_url(value):
    if not value:
        return "sqlite:///reservini.db"
    for prefix in ("postgres://", "postgresql://"):
        if value.startswith(prefix):
            return "postgresql+psycopg://" + value.removeprefix(prefix)
    return value


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = database_url(os.environ.get("DATABASE_URL"))
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    TRUST_PROXY = os.environ.get("TRUST_PROXY") == "1"
    LANGUAGES = {"en": "English", "es": "Español"}
    BABEL_DEFAULT_LOCALE = "en"
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True
    RATELIMIT_STORAGE_URI = "memory://"
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT") or "587")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_SENDER = os.environ.get("MAIL_SENDER") or "Reservini <no-reply@example.com>"
