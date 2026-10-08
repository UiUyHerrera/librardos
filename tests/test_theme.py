def test_no_theme_is_forced_by_default(client):
    assert b"data-theme" not in client.get("/").data


def test_choosing_dark_mode_is_remembered(client):
    response = client.get("/theme/dark?next=/")

    assert response.status_code == 302
    assert "theme=dark" in response.headers["Set-Cookie"]
    assert b'data-theme="dark"' in client.get("/").data


def test_unknown_theme_returns_not_found(client):
    assert client.get("/theme/purple").status_code == 404


def test_changing_theme_never_redirects_to_another_site(client):
    assert client.get("/theme/light?next=//evil.example").headers["Location"] == "/"
