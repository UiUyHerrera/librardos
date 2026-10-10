import re
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import func, select

from reservini.extensions import db
from reservini.models import Booking, BookingStatus, Business, OpeningHours, Plan, Service, User, utc_now
from reservini.notifications import send_due_reminders
from reservini.plans import FREE_MONTHLY_BOOKINGS
from reservini.scheduling import available_slots, bookable_days, day_timeline, to_database_time

WEDNESDAY = date(2026, 1, 14)
LONG_AGO = datetime(2025, 1, 1, tzinfo=UTC)


@pytest.fixture
def business(user):
    business = Business(
        owner=user,
        name="North Side Barbers",
        slug="north-side",
        timezone="America/New_York",
        opening_hours=[OpeningHours(weekday=weekday, opens_at=time(9, 0), closes_at=time(12, 0)) for weekday in range(7)],
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
        created_at=LONG_AGO,
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


def test_slots_skip_the_break_between_two_blocks(business, haircut):
    business.opening_hours.append(OpeningHours(weekday=WEDNESDAY.weekday(), opens_at=time(14, 0), closes_at=time(15, 0)))

    assert slot_times(business, haircut, WEDNESDAY)[-2:] == ["11:00", "14:00"]


def test_timeline_marks_booked_and_closed_times(business, haircut):
    business.opening_hours.append(OpeningHours(weekday=WEDNESDAY.weekday(), opens_at=time(13, 0), closes_at=time(14, 0)))
    add_booking(business, haircut, available_slots(business, haircut, WEDNESDAY, LONG_AGO)[0])

    statuses = [row.status for row in day_timeline(business, haircut, WEDNESDAY, LONG_AGO)]

    assert statuses == ["booked", "booked", "free", "free", "free", "unavailable", "closed", "closed", "free", "unavailable"]


def test_closed_days_have_no_slots(business, haircut):
    business.opening_hours = [hours for hours in business.opening_hours if hours.weekday < 5]

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


@pytest.fixture
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr("reservini.mailer.deliver", sent.append)
    return sent


def test_booking_sends_a_confirmation_email(client, business, haircut, outbox):
    url = tomorrow_url(business, haircut)

    book(client, url, first_slot_value(client.get(url)))

    assert len(outbox) == 1
    assert outbox[0]["To"] == "ana@example.com"
    assert outbox[0]["Subject"] == "Your booking at North Side Barbers"
    assert "Haircut" in outbox[0].get_content()


def test_confirmation_email_uses_the_language_of_the_booking(client, business, haircut, outbox):
    client.get("/language/es")
    url = tomorrow_url(business, haircut)

    book(client, url, first_slot_value(client.get(url)))

    assert outbox[0]["Subject"] == "Tu reserva en North Side Barbers"


def booking_on_wednesday(business, service):
    start = available_slots(business, service, WEDNESDAY, LONG_AGO)[2]
    add_booking(business, service, start)
    return db.session.scalar(select(Booking))


def test_reminder_is_sent_once_on_the_morning_of_the_booking(business, haircut, outbox):
    booking = booking_on_wednesday(business, haircut)
    seven_in_new_york = datetime(2026, 1, 14, 12, 0, tzinfo=UTC)
    eight_thirty_in_new_york = datetime(2026, 1, 14, 13, 30, tzinfo=UTC)

    assert send_due_reminders(seven_in_new_york) == 0
    assert send_due_reminders(eight_thirty_in_new_york) == 1
    assert send_due_reminders(eight_thirty_in_new_york) == 0
    assert booking.reminder_sent_at is not None
    assert outbox[0]["Subject"] == "Today: Haircut at North Side Barbers"


def test_cancelled_bookings_get_no_reminder(business, haircut, outbox):
    booking = booking_on_wednesday(business, haircut)
    booking.status = BookingStatus.CANCELLED
    db.session.commit()

    assert send_due_reminders(datetime(2026, 1, 14, 13, 30, tzinfo=UTC)) == 0


def test_failed_email_does_not_break_the_booking(client, business, haircut, monkeypatch):
    def broken_server(message):
        raise OSError("mail server down")

    monkeypatch.setattr("reservini.mailer.deliver", broken_server)
    url = tomorrow_url(business, haircut)

    response = book(client, url, first_slot_value(client.get(url)))

    assert response.headers["Location"] == "/b/north-side/confirmation"


def log_in_as_owner(client):
    client.post("/login", data={"email": "owner@example.com", "password": "correct-horse"})


def upcoming_booking(business, service):
    start = available_slots(business, service, bookable_days(business, utc_now())[1], utc_now())[0]
    add_booking(business, service, start)
    return db.session.scalar(select(Booking))


def test_owner_sees_upcoming_bookings(client, business, haircut):
    upcoming_booking(business, haircut)
    log_in_as_owner(client)

    response = client.get("/dashboard/")

    assert b"Sam Rivera" in response.data
    assert b"sam@example.com" in response.data


def test_owner_can_cancel_a_booking_and_the_client_is_told(client, business, haircut, outbox):
    booking = upcoming_booking(business, haircut)
    log_in_as_owner(client)

    client.post(f"/dashboard/bookings/{booking.id}/cancel")

    assert booking.status == BookingStatus.CANCELLED
    assert outbox[0]["Subject"] == "Cancelled: Haircut at North Side Barbers"
    assert b"booking-row" not in client.get("/dashboard/").data


def test_owner_cannot_cancel_another_business_booking(client, business, haircut):
    booking = upcoming_booking(business, haircut)
    other = User(email="other@example.com")
    other.set_password("correct-horse")
    db.session.add(other)
    db.session.commit()
    client.post("/login", data={"email": "other@example.com", "password": "correct-horse"})

    assert client.post(f"/dashboard/bookings/{booking.id}/cancel").status_code == 404
    assert booking.status == BookingStatus.CONFIRMED


def fill_free_plan(business, service):
    start = datetime(2030, 1, 1, 9, 0, tzinfo=UTC)
    for number in range(FREE_MONTHLY_BOOKINGS):
        slot_start = start + timedelta(hours=number)
        db.session.add(
            Booking(
                business=business,
                service=service,
                customer_name="Client",
                customer_email="client@example.com",
                starts_at=to_database_time(slot_start),
                ends_at=to_database_time(slot_start + timedelta(minutes=30)),
            )
        )
    db.session.commit()


def test_free_plan_stops_taking_bookings_after_the_monthly_limit(client, business, haircut):
    fill_free_plan(business, haircut)

    response = client.get(tomorrow_url(business, haircut))

    assert b"not taking new bookings this month" in response.data
    assert b'name="slot"' not in response.data


def test_pro_plan_has_no_limit(client, business, haircut):
    fill_free_plan(business, haircut)
    log_in_as_owner(client)
    client.post("/dashboard/plan/pro")

    response = client.get(tomorrow_url(business, haircut))

    assert business.plan == Plan.PRO
    assert b'name="slot"' in response.data
