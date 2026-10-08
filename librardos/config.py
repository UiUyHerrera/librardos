import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///librardos.db")
    LANGUAGES = {"en": "English", "es": "Español"}
    BABEL_DEFAULT_LOCALE = "en"
