import re
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select

from reservini.extensions import db
from reservini.models import Booking, Business, Service, utc_now
from reservini.scheduling import available_slots, bookable_days, to_database_time

WEDNESDAY = date(2026, 1, 14)
LONG_AGO = datetime(2025, 1, 1, tzinfo=UTC)


@pytest.fixture
def business(user):
    business = Business(
        owner=user,
        name="North Side Barbers",
        slug="north-side",
        timezone="America/New_York",
        opens_at=time(9, 0),
        closes_at=time(12, 0),
        open_days="0123456",
    )
    db.session.add(business)
    db.session.commit()
    return business


@pytest.fixture
def haircut(business):
    service = Service(business=business, name="Haircut", duration_minutes=60, price_cents=2500)
    db.session.add(service)
    db.session.commit()
    return service


def add_booking(business, service, starts_at):
    booking = Booking(
        business=business,
        service=service,
        customer_name="Sam Rivera",
        customer_email="sam@example.com",
        starts_at=to_database_time(starts_at),
        ends_at=to_database_time(starts_at + timedelta(minutes=service.duration_minutes)),
    )
    db.session.add(booking)
    db.session.commit()


def slot_times(business, service, day, now=LONG_AGO):
    return [slot.strftime("%H:%M") for slot in available_slots(business, service, day, now)]


def test_slots_fit_inside_opening_hours(business, haircut):
    assert slot_times(business, haircut, WEDNESDAY) == ["09:00", "09:30", "10:00", "10:30", "11:00"]


def test_slots_use_the_business_time_zone(business, haircut):
    first_slot = available_slots(business, haircut, WEDNESDAY, LONG_AGO)[0]

    assert to_database_time(first_slot) == datetime(2026, 1, 14, 14, 0)


def test_booked_time_and_overlapping_slots_disappear(business, haircut):
    add_booking(business, haircut, available_slots(business, haircut, WEDNESDAY, LONG_AGO)[2])

    assert slot_times(business, haircut, WEDNESDAY) == ["09:00", "11:00"]


def test_past_slots_are_not_offered(business, haircut):
    ten_fifteen_in_new_york = datetime(2026, 1, 14, 15, 15, tzinfo=UTC)

    assert slot_times(business, haircut, WEDNESDAY, now=ten_fifteen_in_new_york) == ["10:30", "11:00"]


def test_closed_days_have_no_slots(business, haircut):
    business.open_days = "01234"

    assert slot_times(business, haircut, date(2026, 1, 17)) == []


def test_business_page_lists_only_active_services(client, business, haircut):
    hidden = Service(business=business, name="Hidden massage", duration_minutes=30, price_cents=100, is_active=False)
    db.session.add(hidden)
    db.session.commit()

    response = client.get("/b/north-side")

    assert b"Haircut" in response.data
    assert b"Hidden massage" not in response.data
    assert client.get(f"/b/north-side/services/{hidden.id}").status_code == 404


def test_unknown_business_returns_not_found(client):
    assert client.get("/b/nobody-here").status_code == 404


def tomorrow_url(business, service):
    tomorrow = bookable_days(business, utc_now())[1]
    return f"/b/{business.slug}/services/{service.id}?day={tomorrow.isoformat()}"


def first_slot_value(response):
    return re.search(r'<input[^>]*name="slot"[^>]*value="([^"]+)"', response.text).group(1)


def book(client, url, slot):
    return client.post(url, data={"slot": slot, "customer_name": "Ana", "customer_email": "ana@example.com"})


def test_client_can_book_a_free_time(client, business, haircut):
    url = tomorrow_url(business, haircut)
    slot = first_slot_value(client.get(url))

    response = book(client, url, slot)

    assert response.headers["Location"] == "/b/north-side/confirmation"
    assert b"You are booked" in client.get("/b/north-side/confirmation").data
    assert db.session.scalar(select(func.count(Booking.id))) == 1


def test_the_same_time_cannot_be_booked_twice(client, business, haircut):
    url = tomorrow_url(business, haircut)
    slot = first_slot_value(client.get(url))

    book(client, url, slot)
    second = book(client, url, slot)

    assert second.status_code == 200
    assert db.session.scalar(select(func.count(Booking.id))) == 1
