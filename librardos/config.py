import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    LANGUAGES = {"en": "English", "es": "Español"}
    BABEL_DEFAULT_LOCALE = "en"
