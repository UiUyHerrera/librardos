from collections import namedtuple
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from reservini.extensions import db
from reservini.models import Booking, BookingStatus

SLOT_STEP = timedelta(minutes=30)
BOOKING_WINDOW_DAYS = 14

TimelineRow = namedtuple("TimelineRow", ["starts_at", "status"])


def to_database_time(moment):
    return moment.astimezone(UTC).replace(tzinfo=None)


def from_database_time(moment):
    return moment.replace(tzinfo=UTC)


def bookable_days(business, now):
    today = now.astimezone(ZoneInfo(business.timezone)).date()
    days = (today + timedelta(days=offset) for offset in range(BOOKING_WINDOW_DAYS))
    return [day for day in days if day.weekday() in business.open_weekdays]


def opening_ranges(business, day):
    zone = ZoneInfo(business.timezone)
    return [
        (datetime.combine(day, opens, tzinfo=zone), datetime.combine(day, closes, tzinfo=zone))
        for opens, closes in business.hours_on(day.weekday())
    ]


def available_slots(business, service, day, now):
    ranges = opening_ranges(business, day)
    if not ranges:
        return []

    length = timedelta(minutes=service.duration_minutes)
    busy = confirmed_bookings_between(business, ranges[0][0], ranges[-1][1])

    slots = []
    for opens, closes in ranges:
        start = opens
        while start + length <= closes:
            if start > now and not any(overlaps(start, start + length, booking) for booking in busy):
                slots.append(start)
            start += SLOT_STEP
    return slots


def day_timeline(business, service, day, now):
    ranges = opening_ranges(business, day)
    if not ranges:
        return []

    free = set(available_slots(business, service, day, now))
    busy = confirmed_bookings_between(business, ranges[0][0], ranges[-1][1])

    rows = []
    moment = ranges[0][0]
    while moment < ranges[-1][1]:
        if moment in free:
            status = "free"
        elif any(overlaps(moment, moment + SLOT_STEP, booking) for booking in busy):
            status = "booked"
        elif not any(opens <= moment < closes for opens, closes in ranges):
            status = "closed"
        else:
            status = "unavailable"
        rows.append(TimelineRow(moment, status))
        moment += SLOT_STEP
    return rows


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
