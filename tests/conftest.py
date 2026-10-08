import pytest

from reservini import create_app
from reservini.config import Config
from reservini.extensions import db
from reservini.models import User

USER_EMAIL = "owner@example.com"
USER_PASSWORD = "correct-horse"


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "testing-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


class RateLimitedConfig(TestingConfig):
    RATELIMIT_ENABLED = True


class CsrfProtectedConfig(TestingConfig):
    WTF_CSRF_ENABLED = True


def running_app(config_class):
    app = create_app(config_class)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app():
    yield from running_app(TestingConfig)


@pytest.fixture
def rate_limited_app():
    yield from running_app(RateLimitedConfig)


@pytest.fixture
def csrf_protected_app():
    yield from running_app(CsrfProtectedConfig)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    user = User(email=USER_EMAIL)
    user.set_password(USER_PASSWORD)
    db.session.add(user)
    db.session.commit()
    return user
