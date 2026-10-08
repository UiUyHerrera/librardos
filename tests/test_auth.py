from sqlalchemy import func, select

from librardos.extensions import db
from librardos.models import User

USER_EMAIL = "owner@example.com"
USER_PASSWORD = "correct-horse"


def register(client, email="new@example.com", password=USER_PASSWORD, confirm_password=USER_PASSWORD):
    return client.post(
        "/register",
        data={"email": email, "password": password, "confirm_password": confirm_password},
    )


def login(client, email=USER_EMAIL, password=USER_PASSWORD, next_url=None):
    url = "/login" if next_url is None else f"/login?next={next_url}"
    return client.post(url, data={"email": email, "password": password})


def count_users():
    return db.session.scalar(select(func.count(User.id)))


def test_register_creates_account_and_logs_in(client):
    response = register(client, email="  New@Example.com ")

    assert response.status_code == 302
    user = db.session.scalar(select(User))
    assert user.email == "new@example.com"
    assert user.password_hash != USER_PASSWORD
    assert user.check_password(USER_PASSWORD)
    assert b"Log out" in client.get("/").data


def test_register_rejects_existing_email(client, user):
    response = register(client, email="OWNER@example.com")

    assert response.status_code == 200
    assert b"An account with this email already exists." in response.data
    assert count_users() == 1


def test_register_rejects_short_password(client):
    response = register(client, password="short", confirm_password="short")

    assert b"Use between 8 and 128 characters." in response.data
    assert count_users() == 0


def test_register_rejects_different_passwords(client):
    response = register(client, confirm_password="another-horse")

    assert b"Passwords do not match." in response.data
    assert count_users() == 0


def test_register_rejects_invalid_email(client):
    response = register(client, email="not-an-email")

    assert b"Invalid email address." in response.data
    assert count_users() == 0


def test_login_with_correct_password(client, user):
    response = login(client)

    assert response.status_code == 302
    assert response.headers["Location"] == "/dashboard/"
    assert b"Log out" in client.get("/").data


def test_login_shows_the_same_error_for_wrong_password_and_unknown_email(client, user):
    wrong_password = login(client, password="wrong-password")
    unknown_email = login(client, email="nobody@example.com")

    assert b"Wrong email or password." in wrong_password.data
    assert b"Wrong email or password." in unknown_email.data


def test_login_follows_a_safe_next_url(client, user):
    assert login(client, next_url="/somewhere").headers["Location"] == "/somewhere"


def test_login_ignores_an_external_next_url(client, user):
    assert login(client, next_url="//evil.example").headers["Location"] == "/dashboard/"


def test_logout_only_accepts_post(client, user):
    login(client)

    assert client.get("/logout").status_code == 405
    client.post("/logout")
    assert b"Log out" not in client.get("/").data


def test_login_is_rate_limited(rate_limited_app):
    client = rate_limited_app.test_client()

    statuses = [login(client, password="wrong-password").status_code for _ in range(6)]

    assert statuses == [200, 200, 200, 200, 200, 429]


def test_forms_reject_posts_without_csrf_token(csrf_protected_app):
    client = csrf_protected_app.test_client()

    response = login(client)

    assert response.status_code == 400
    assert b"The form expired" in response.data
