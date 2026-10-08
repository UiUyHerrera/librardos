from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from reservini.extensions import db
from reservini.models import Booking, BookingStatus

SLOT_STEP = timedelta(minutes=30)
BOOKING_WINDOW_DAYS = 14


def to_database_time(moment):
    return moment.astimezone(UTC).replace(tzinfo=None)


def from_database_time(moment):
    return moment.replace(tzinfo=UTC)


def bookable_days(business, now):
    today = now.astimezone(ZoneInfo(business.timezone)).date()
    days = (today + timedelta(days=offset) for offset in range(BOOKING_WINDOW_DAYS))
    return [day for day in days if day.weekday() in business.open_weekdays]


def available_slots(business, service, day, now):
    if day.weekday() not in business.open_weekdays:
        return []

    zone = ZoneInfo(business.timezone)
    opens = datetime.combine(day, business.opens_at, tzinfo=zone)
    closes = datetime.combine(day, business.closes_at, tzinfo=zone)
    length = timedelta(minutes=service.duration_minutes)
    busy = confirmed_bookings_between(business, opens, closes)

    slots = []
    start = opens
    while start + length <= closes:
        end = start + length
        if start > now and not any(overlaps(start, end, booking) for booking in busy):
            slots.append(start)
        start += SLOT_STEP
    return slots


def confirmed_bookings_between(business, start, end):
    query = select(Booking).where(
        Booking.business_id == business.id,
        Booking.status == BookingStatus.CONFIRMED,
        Booking.starts_at < to_database_time(end),
        Booking.ends_at > to_database_time(start),
    )
    return db.session.scalars(query).all()


def overlaps(start, end, booking):
    return start < from_database_time(booking.ends_at) and end > from_database_time(booking.starts_at)


def parse_day(value, allowed_days):
    try:
        day = date.fromisoformat(value or "")
    except ValueError:
        return allowed_days[0] if allowed_days else None
    return day if day in allowed_days else (allowed_days[0] if allowed_days else None)
