from reservini.config import database_url


def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Your clients book on their own" in response.data


def test_responses_include_security_headers(client):
    headers = client.get("/").headers

    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_missing_page_shows_friendly_error(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_postgres_urls_use_the_psycopg_driver():
    assert database_url("postgres://user:secret@host/db") == "postgresql+psycopg://user:secret@host/db"
    assert database_url("postgresql://user:secret@host/db") == "postgresql+psycopg://user:secret@host/db"
    assert database_url(None) == "sqlite:///reservini.db"


def test_https_responses_ask_browsers_to_stay_on_https(client):
    headers = client.get("/", base_url="https://localhost").headers

    assert headers["Strict-Transport-Security"].startswith("max-age=")


def test_reminder_task_is_hidden_without_the_secret(app, client):
    app.config["CRON_SECRET"] = "cron-secret"

    assert client.get("/tasks/send-reminders").status_code == 404
    assert client.get("/tasks/send-reminders", headers={"Authorization": "Bearer wrong"}).status_code == 404


def test_reminder_task_runs_with_the_secret(app, client):
    app.config["CRON_SECRET"] = "cron-secret"

    response = client.get("/tasks/send-reminders", headers={"Authorization": "Bearer cron-secret"})

    assert response.status_code == 200
    assert response.json == {"sent": 0}
