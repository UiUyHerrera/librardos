from flask_babel import Babel
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


babel = Babel()
db = SQLAlchemy(model_class=Base)
