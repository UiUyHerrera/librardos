import hmac

from flask import Blueprint, abort, current_app, jsonify, request

from reservini.extensions import csrf
from reservini.models import utc_now
from reservini.notifications import send_due_reminders

bp = Blueprint("tasks", __name__, url_prefix="/tasks")


@bp.get("/send-reminders")
@csrf.exempt
def send_reminders():
    secret = current_app.config["CRON_SECRET"]
    authorization = request.headers.get("Authorization", "")
    if not secret or not hmac.compare_digest(authorization, f"Bearer {secret}"):
        abort(404)
    return jsonify(sent=send_due_reminders(utc_now()))
