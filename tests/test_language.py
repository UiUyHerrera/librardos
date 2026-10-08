import pytest


def test_english_is_the_default(client):
    response = client.get("/")

    assert b'<html lang="en">' in response.data


def test_browser_language_is_used(client):
    response = client.get("/", headers={"Accept-Language": "es-MX,es;q=0.9"})

    assert b'<html lang="es">' in response.data
    assert "Tus clientes reservan solos" in response.text


def test_changing_language_saves_a_cookie(client):
    response = client.get("/language/es?next=/")

    assert response.status_code == 302
    assert "language=es" in response.headers["Set-Cookie"]
    assert "HttpOnly" in response.headers["Set-Cookie"]
    assert b'<html lang="es">' in client.get("/").data


def test_unknown_language_returns_not_found(client):
    assert client.get("/language/xx").status_code == 404


@pytest.mark.parametrize(
    "next_url",
    ["//evil.example", "https://evil.example", "/\\evil.example", "/%09/evil.example"],
)
def test_changing_language_never_redirects_to_another_site(client, next_url):
    response = client.get(f"/language/en?next={next_url}")

    assert response.headers["Location"] == "/"
