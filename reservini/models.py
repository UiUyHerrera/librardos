import enum
from datetime import UTC, datetime, time
from decimal import ROUND_HALF_UP, Decimal

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from reservini.extensions import db


def utc_now():
    return datetime.now(UTC)


class Plan(enum.StrEnum):
    FREE = "free"
    PRO = "pro"


class BookingStatus(enum.StrEnum):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    business: Mapped["Business | None"] = relationship(back_populates="owner")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Business(db.Model):
    __tablename__ = "businesses"
    __table_args__ = (
        CheckConstraint("opens_at < closes_at", name="opens_before_closing"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(60), unique=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    opens_at: Mapped[time] = mapped_column(default=time(9, 0))
    closes_at: Mapped[time] = mapped_column(default=time(18, 0))
    open_days: Mapped[str] = mapped_column(String(7), default="01234")
    plan: Mapped[Plan] = mapped_column(default=Plan.FREE)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    owner: Mapped[User] = relationship(back_populates="business")

    @property
    def open_weekdays(self):
        return [int(day) for day in self.open_days]

    @open_weekdays.setter
    def open_weekdays(self, days):
        self.open_days = "".join(str(day) for day in sorted(set(days)))
    services: Mapped[list["Service"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        order_by="Service.name",
    )
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
        order_by="Booking.starts_at",
    )


class Service(db.Model):
    __tablename__ = "services"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="positive_duration"),
        CheckConstraint("price_cents >= 0", name="non_negative_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    duration_minutes: Mapped[int]
    price_cents: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)

    business: Mapped[Business] = relationship(back_populates="services")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="service")

    @property
    def price(self):
        return Decimal(self.price_cents) / 100

    @price.setter
    def price(self, value):
        self.price_cents = int((Decimal(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class Booking(db.Model):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="starts_before_ending"),
        Index(
            "one_confirmed_booking_per_start",
            "business_id",
            "starts_at",
            unique=True,
            sqlite_where=text("status = 'CONFIRMED'"),
            postgresql_where=text("status = 'CONFIRMED'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    customer_name: Mapped[str] = mapped_column(String(100))
    customer_email: Mapped[str] = mapped_column(String(255))
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime]
    status: Mapped[BookingStatus] = mapped_column(default=BookingStatus.CONFIRMED)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    business: Mapped[Business] = relationship(back_populates="bookings")
    service: Mapped[Service] = relationship(back_populates="bookings")
