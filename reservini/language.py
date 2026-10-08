from flask import Blueprint, abort, current_app, redirect, request, url_for
from flask_babel import get_locale

from reservini.preferences import remember_preference
from reservini.security import safe_next_url

bp = Blueprint("language", __name__)

LANGUAGE_COOKIE = "language"


def select_locale():
    languages = current_app.config["LANGUAGES"]
    language = request.cookies.get(LANGUAGE_COOKIE)
    if language in languages:
        return language
    return request.accept_languages.best_match(list(languages))


@bp.app_context_processor
def inject_current_language():
    return {"current_language": str(get_locale())}


@bp.get("/language/<code>")
def change_language(code):
    if code not in current_app.config["LANGUAGES"]:
        abort(404)

    response = redirect(safe_next_url(request.args.get("next"), url_for("main.index")))
    return remember_preference(response, LANGUAGE_COOKIE, code)
