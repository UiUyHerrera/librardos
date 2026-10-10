from datetime import timedelta
from zoneinfo import ZoneInfo

import click
from flask import render_template
from flask.cli import with_appcontext
from flask_babel import force_locale
from flask_babel import gettext as _
from sqlalchemy import select

from reservini.extensions import db
from reservini.mailer import send_email
from reservini.models import Booking, BookingStatus, utc_now
from reservini.scheduling import from_database_time, to_database_time

REMINDER_HOUR = 8


def send_booking_confirmation(booking):
    with force_locale(booking.language):
        subject = _("Your booking at %(business)s", business=booking.business.name)
        body = render_template("email/booking_confirmed.txt", booking=booking)
    return send_email(booking.customer_email, subject, body)


def send_booking_reminder(booking):
    with force_locale(booking.language):
        subject = _("Today: %(service)s at %(business)s", service=booking.service.name, business=booking.business.name)
        body = render_template("email/booking_reminder.txt", booking=booking)
    return send_email(booking.customer_email, subject, body)


def send_booking_cancellation(booking):
    with force_locale(booking.language):
        subject = _("Cancelled: %(service)s at %(business)s", service=booking.service.name, business=booking.business.name)
        body = render_template("email/booking_cancelled.txt", booking=booking)
    return send_email(booking.customer_email, subject, body)


def is_reminder_due(booking, now):
    zone = ZoneInfo(booking.business.timezone)
    local_now = now.astimezone(zone)
    starts_at = from_database_time(booking.starts_at).astimezone(zone)
    booked_at = from_database_time(booking.created_at).astimezone(zone)
    return (
        starts_at.date() == local_now.date()
        and local_now.hour >= REMINDER_HOUR
        and booked_at.date() < starts_at.date()
    )


def send_due_reminders(now):
    query = select(Booking).where(
        Booking.status == BookingStatus.CONFIRMED,
        Booking.reminder_sent_at.is_(None),
        Booking.starts_at > to_database_time(now),
        Booking.starts_at < to_database_time(now + timedelta(days=1)),
    )
    sent = 0
    for booking in db.session.scalars(query):
        if is_reminder_due(booking, now) and send_booking_reminder(booking):
            booking.reminder_sent_at = to_database_time(now)
            sent += 1
    db.session.commit()
    return sent


@click.command("send-reminders")
@with_appcontext
def send_reminders_command():
    sent = send_due_reminders(utc_now())
    click.echo(f"Sent {sent} reminders.")
