import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///reservini.db")
    LANGUAGES = {"en": "English", "es": "Español"}
    BABEL_DEFAULT_LOCALE = "en"
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = True
    RATELIMIT_STORAGE_URI = "memory://"
