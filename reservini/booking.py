from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from babel.dates import format_date, format_datetime
from flask import Blueprint, abort, redirect, render_template, request, session, url_for
from flask_babel import get_locale
from flask_babel import gettext as _
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from reservini.extensions import db, limiter
from reservini.forms import BookingForm
from reservini.models import Booking, Business, Service, utc_now
from reservini.notifications import send_booking_confirmation
from reservini.plans import can_take_booking
from reservini.scheduling import (
    available_slots,
    bookable_days,
    day_timeline,
    from_database_time,
    parse_day,
    to_database_time,
)

bp = Blueprint("booking", __name__, url_prefix="/b")

LAST_BOOKING_KEY = "last_booking_id"


@bp.get("/<slug>")
def business_page(slug):
    business = business_or_404(slug)
    services = [service for service in business.services if service.is_active]
    return render_template("booking/business.html", business=business, services=services)


@bp.route("/<slug>/services/<int:service_id>", methods=["GET", "POST"])
@limiter.limit("20 per hour", methods=["POST"])
def book_service(slug, service_id):
    business = business_or_404(slug)
    service = active_service_or_404(business, service_id)
    now = utc_now()
    days = bookable_days(business, now)
    timelines = [(day, day_timeline(business, service, day, now)) for day in days]
    slots = [row.starts_at for _day, rows in timelines for row in rows if row.status == "free"]
    days_with_slots = [day for day, rows in timelines if any(row.status == "free" for row in rows)]
    selected_day = parse_day(request.args.get("day"), days)
    if "day" not in request.args and days_with_slots:
        selected_day = days_with_slots[0]

    accepting_bookings = can_take_booking(business, now)
    form = BookingForm()
    form.slot.choices = [(slot.isoformat(), slot.strftime("%H:%M")) for slot in slots]

    if accepting_bookings and form.validate_on_submit():
        booking = create_booking(business, service, form)
        if booking is None:
            form.slot.errors.append(_("Someone just took that time. Pick another one."))
        else:
            session[LAST_BOOKING_KEY] = booking.id
            return redirect(url_for("booking.confirmation", slug=business.slug))

    return render_template(
        "booking/book.html",
        business=business,
        service=service,
        selected_day=selected_day,
        timelines=timelines,
        accepting_bookings=accepting_bookings,
        form=form,
    )


@bp.get("/<slug>/confirmation")
def confirmation(slug):
    business = business_or_404(slug)
    booking = db.session.get(Booking, session.get(LAST_BOOKING_KEY, 0))
    if booking is None or booking.business_id != business.id:
        return redirect(url_for("booking.business_page", slug=business.slug))
    return render_template("booking/confirmation.html", business=business, booking=booking)


@bp.app_template_filter("local_time")
def local_time(moment, business, pattern="EEEE d MMMM, HH:mm"):
    return format_datetime(
        from_database_time(moment),
        pattern,
        tzinfo=ZoneInfo(business.timezone),
        locale=get_locale(),
    )


@bp.app_template_filter("day_label")
def day_label(day, pattern="EEE d MMM"):
    return format_date(day, pattern, locale=get_locale())


def create_booking(business, service, form):
    starts_at = datetime.fromisoformat(form.slot.data)
    db.session.execute(select(Business).where(Business.id == business.id).with_for_update())
    if starts_at not in available_slots(business, service, starts_at.date(), utc_now()):
        db.session.rollback()
        return None

    booking = Booking(
        business=business,
        service=service,
        customer_name=form.customer_name.data,
        customer_email=form.customer_email.data,
        starts_at=to_database_time(starts_at),
        ends_at=to_database_time(starts_at + timedelta(minutes=service.duration_minutes)),
        language=str(get_locale()),
    )
    db.session.add(booking)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None
    send_booking_confirmation(booking)
    return booking


def business_or_404(slug):
    business = db.session.scalar(select(Business).filter_by(slug=slug))
    if business is None:
        abort(404)
    return business


def active_service_or_404(business, service_id):
    service = db.session.get(Service, service_id)
    if service is None or service.business_id != business.id or not service.is_active:
        abort(404)
    return service
