from sqlalchemy import func, select

from reservini.extensions import db
from reservini.models import Booking, Plan
from reservini.scheduling import to_database_time

FREE_MONTHLY_BOOKINGS = 20


def month_start(now):
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def monthly_booking_count(business, now):
    query = select(func.count(Booking.id)).where(
        Booking.business_id == business.id,
        Booking.created_at >= to_database_time(month_start(now)),
    )
    return db.session.scalar(query)


def can_take_booking(business, now):
    return business.plan == Plan.PRO or monthly_booking_count(business, now) < FREE_MONTHLY_BOOKINGS
