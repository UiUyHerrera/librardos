from flask_babel import Babel
from flask_babel import lazy_gettext as _l
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


babel = Babel()
csrf = CSRFProtect()
db = SQLAlchemy(model_class=Base)
limiter = Limiter(key_func=get_remote_address)
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = _l("Log in to see this page.")
