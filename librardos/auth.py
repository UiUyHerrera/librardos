from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from librardos.extensions import db, limiter, login_manager
from librardos.forms import LoginForm, RegisterForm
from librardos.models import User
from librardos.security import safe_next_url

bp = Blueprint("auth", __name__)

DUMMY_PASSWORD_HASH = generate_password_hash("not-a-real-password")


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            form.email.errors.append(_("An account with this email already exists."))
        else:
            login_user(user)
            flash(_("Your account is ready."))
            return redirect(url_for("main.index"))

    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(select(User).filter_by(email=form.email.data))
        if user is None:
            check_password_hash(DUMMY_PASSWORD_HASH, form.password.data)
        elif user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(safe_next_url(request.args.get("next"), url_for("main.index")))
        form.form_errors.append(_("Wrong email or password."))

    return render_template("auth/login.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash(_("You have logged out."))
    return redirect(url_for("main.index"))
