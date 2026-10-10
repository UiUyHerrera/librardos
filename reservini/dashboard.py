from babel.dates import get_day_names
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_babel import format_currency, get_locale
from flask_babel import gettext as _
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from reservini.extensions import db
from reservini.forms import BusinessForm, ServiceForm
from reservini.models import Booking, BookingStatus, Business, Plan, Service, utc_now
from reservini.notifications import send_booking_cancellation
from reservini.plans import FREE_MONTHLY_BOOKINGS, monthly_booking_count
from reservini.scheduling import to_database_time

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@bp.app_template_filter("money")
def money(amount, currency):
    return format_currency(amount, currency)


@bp.app_template_filter("day_names")
def day_names(days):
    names = get_day_names("abbreviated", locale=get_locale())
    return ", ".join(names[day].capitalize() for day in days)


@bp.app_template_filter("hours_text")
def hours_text(ranges):
    return ", ".join(f"{opens:%H:%M}–{closes:%H:%M}" for opens, closes in ranges)


@bp.get("/")
@login_required
def index():
    business = current_user.business
    if business is None:
        return redirect(url_for("dashboard.create_business"))

    now = utc_now()
    upcoming = db.session.scalars(
        select(Booking)
        .where(
            Booking.business_id == business.id,
            Booking.status == BookingStatus.CONFIRMED,
            Booking.ends_at > to_database_time(now),
        )
        .order_by(Booking.starts_at)
        .limit(50)
    ).all()
    return render_template(
        "dashboard/index.html",
        business=business,
        upcoming=upcoming,
        bookings_this_month=monthly_booking_count(business, now),
        monthly_limit=FREE_MONTHLY_BOOKINGS,
    )


@bp.route("/business/new", methods=["GET", "POST"])
@login_required
def create_business():
    if current_user.business is not None:
        return redirect(url_for("dashboard.index"))

    form = BusinessForm()
    if form.validate_on_submit():
        business = Business(owner=current_user)
        form.apply_to(business)
        if save_business(business, form):
            flash(_("Your business is ready. Now add the services you offer."))
            return redirect(url_for("dashboard.index"))

    return render_template("dashboard/business_form.html", form=form, title=_("Set up your business"), submit_label=_("Create business"))


@bp.route("/business/edit", methods=["GET", "POST"])
@login_required
def edit_business():
    business = business_or_404()
    form = BusinessForm(obj=business, business=business)
    if form.validate_on_submit():
        form.apply_to(business)
        if save_business(business, form):
            flash(_("Business details saved."))
            return redirect(url_for("dashboard.index"))

    return render_template("dashboard/business_form.html", form=form, title=_("Edit your business"), submit_label=_("Save changes"))


@bp.route("/services/new", methods=["GET", "POST"])
@login_required
def create_service():
    business = business_or_404()
    form = ServiceForm()
    if form.validate_on_submit():
        service = Service(business=business)
        form.populate_obj(service)
        db.session.add(service)
        db.session.commit()
        flash(_("Service added."))
        return redirect(url_for("dashboard.index"))

    return render_template("dashboard/service_form.html", form=form, title=_("Add a service"), submit_label=_("Add service"))


@bp.route("/services/<int:service_id>/edit", methods=["GET", "POST"])
@login_required
def edit_service(service_id):
    service = owned_service_or_404(service_id)
    form = ServiceForm(obj=service)
    if form.validate_on_submit():
        form.populate_obj(service)
        db.session.commit()
        flash(_("Service saved."))
        return redirect(url_for("dashboard.index"))

    return render_template("dashboard/service_form.html", form=form, title=_("Edit service"), submit_label=_("Save changes"))


@bp.post("/services/<int:service_id>/toggle")
@login_required
def toggle_service(service_id):
    service = owned_service_or_404(service_id)
    service.is_active = not service.is_active
    db.session.commit()
    if service.is_active:
        flash(_("%(name)s is bookable again.", name=service.name))
    else:
        flash(_("%(name)s is hidden from your booking page.", name=service.name))
    return redirect(url_for("dashboard.index"))


@bp.route("/services/<int:service_id>/delete", methods=["GET", "POST"])
@login_required
def delete_service(service_id):
    service = owned_service_or_404(service_id)
    if service.bookings:
        flash(_("%(name)s has bookings, so it can only be hidden.", name=service.name))
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        db.session.delete(service)
        db.session.commit()
        flash(_("%(name)s was deleted.", name=service.name))
        return redirect(url_for("dashboard.index"))

    return render_template("dashboard/delete_service.html", service=service)


@bp.post("/bookings/<int:booking_id>/cancel")
@login_required
def cancel_booking(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking is None or booking.business.owner_id != current_user.id:
        abort(404)

    if booking.status == BookingStatus.CONFIRMED:
        booking.status = BookingStatus.CANCELLED
        db.session.commit()
        send_booking_cancellation(booking)
        flash(_("Booking cancelled. We let %(name)s know by email.", name=booking.customer_name))
    return redirect(url_for("dashboard.index"))


@bp.post("/plan/<name>")
@login_required
def change_plan(name):
    business = business_or_404()
    plans = {"free": Plan.FREE, "pro": Plan.PRO}
    if name not in plans:
        abort(404)

    business.plan = plans[name]
    db.session.commit()
    if business.plan == Plan.PRO:
        flash(_("You are on the Pro plan. There is no booking limit now."))
    else:
        flash(_("You are back on the Free plan."))
    return redirect(url_for("dashboard.index"))


def business_or_404():
    if current_user.business is None:
        abort(404)
    return current_user.business


def owned_service_or_404(service_id):
    service = db.session.get(Service, service_id)
    if service is None or service.business.owner_id != current_user.id:
        abort(404)
    return service


def save_business(business, form):
    db.session.add(business)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        form.slug.errors.append(_("This address is already taken."))
        return False
    return True
