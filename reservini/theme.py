from flask import Blueprint, abort, redirect, request, url_for

from reservini.preferences import remember_preference
from reservini.security import safe_next_url

bp = Blueprint("theme", __name__)

THEME_COOKIE = "theme"
THEMES = ("light", "dark")


@bp.app_context_processor
def inject_current_theme():
    theme = request.cookies.get(THEME_COOKIE)
    return {"current_theme": theme if theme in THEMES else None}


@bp.get("/theme/<name>")
def change_theme(name):
    if name not in THEMES:
        abort(404)

    response = redirect(safe_next_url(request.args.get("next"), url_for("main.index")))
    return remember_preference(response, THEME_COOKIE, name)
