from flask import Blueprint, render_template
from flask_babel import gettext as _
from flask_wtf.csrf import CSRFError

bp = Blueprint("errors", __name__)


@bp.app_errorhandler(404)
def page_not_found(error):
    return render_error(404, _("Page not found"), _("Check the address or go back to the home page."))


@bp.app_errorhandler(429)
def too_many_requests(error):
    return render_error(429, _("Too many attempts"), _("Wait a minute and try again."))


@bp.app_errorhandler(CSRFError)
def form_expired(error):
    return render_error(400, _("The form expired"), _("Reload the page and try again."))


def render_error(status_code, title, message):
    return render_template("error.html", title=title, message=message), status_code
