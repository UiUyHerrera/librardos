from flask import Flask

from reservini.auth import bp as auth_bp
from reservini.config import Config
from reservini.dashboard import bp as dashboard_bp
from reservini.database import init_db_command
from reservini.errors import bp as errors_bp
from reservini.extensions import babel, csrf, db, limiter, login_manager
from reservini.language import bp as language_bp
from reservini.language import select_locale
from reservini.main import bp as main_bp
from reservini.models import Booking, Business, Service, User
from reservini.security import add_security_headers
from reservini.theme import bp as theme_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is not set")

    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    babel.init_app(app, locale_selector=select_locale)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(language_bp)
    app.register_blueprint(theme_bp)
    app.register_blueprint(errors_bp)
    app.after_request(add_security_headers)
    app.shell_context_processor(make_shell_context)
    app.cli.add_command(init_db_command)

    return app


def make_shell_context():
    return {
        "db": db,
        "User": User,
        "Business": Business,
        "Service": Service,
        "Booking": Booking,
    }
