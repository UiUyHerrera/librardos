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
