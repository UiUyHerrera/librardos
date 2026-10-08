from flask import Flask

from librardos.config import Config
from librardos.database import init_db_command
from librardos.extensions import babel, db
from librardos.language import bp as language_bp
from librardos.language import select_locale
from librardos.main import bp as main_bp
from librardos.models import Booking, Business, Service, User

CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "style-src 'self' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data:",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY is not set")

    db.init_app(app)
    babel.init_app(app, locale_selector=select_locale)

    app.register_blueprint(main_bp)
    app.register_blueprint(language_bp)
    app.after_request(add_security_headers)
    app.shell_context_processor(make_shell_context)
    app.cli.add_command(init_db_command)

    return app


def add_security_headers(response):
    response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


def make_shell_context():
    return {
        "db": db,
        "User": User,
        "Business": Business,
        "Service": Service,
        "Booking": Booking,
    }
