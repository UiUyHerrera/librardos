from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import select

from reservini.extensions import db
from reservini.models import Booking, Business, Service, User

USER_EMAIL = "owner@example.com"
USER_PASSWORD = "correct-horse"

BUSINESS_DATA = {
    "name": "North Side Barbers",
    "slug": "north-side",
    "hours-0": "09:00-13:00, 15:00-19:00",
    "hours-1": "",
    "hours-2": "10:00-18:00",
    "hours-3": "",
    "hours-4": "09:00-13:00",
    "hours-5": "",
    "hours-6": "",
    "timezone": "America/New_York",
    "currency": "USD",
}


@pytest.fixture
def owner_client(client, user):
    client.post("/login", data={"email": USER_EMAIL, "password": USER_PASSWORD})
    return client


@pytest.fixture
def business(user):
    business = Business(owner=user, name="North Side Barbers", slug="north-side")
    db.session.add(business)
    db.session.commit()
    return business


@pytest.fixture
def service(business):
    service = Service(business=business, name="Haircut", duration_minutes=30, price_cents=2500)
    db.session.add(service)
    db.session.commit()
    return service


@pytest.fixture
def other_service():
    other_owner = User(email="other@example.com")
    other_owner.set_password(USER_PASSWORD)
    other_business = Business(owner=other_owner, name="Other Shop", slug="other-shop")
    other_service = Service(business=other_business, name="Massage", duration_minutes=60, price_cents=6000)
    db.session.add_all([other_owner, other_business, other_service])
    db.session.commit()
    return other_service


def test_dashboard_requires_login(client):
    response = client.get("/dashboard/")

    assert response.status_code == 302
    assert response.headers["Location"].startswith("/login")


def test_owner_without_business_is_sent_to_set_it_up(owner_client):
    response = owner_client.get("/dashboard/")

    assert response.headers["Location"] == "/dashboard/business/new"


def test_create_business(owner_client, user):
    response = owner_client.post("/dashboard/business/new", data=BUSINESS_DATA)

    assert response.status_code == 302
    business = db.session.scalar(select(Business))
    assert business.owner == user
    assert business.open_weekdays == [0, 2, 4]
    assert business.hours_on(0) == [(time(9, 0), time(13, 0)), (time(15, 0), time(19, 0))]
    assert business.timezone == "America/New_York"


@pytest.mark.parametrize("slug", ["No Spaces", "ab", "trailing-", "émoji"])
def test_create_business_rejects_bad_addresses(owner_client, slug):
    response = owner_client.post("/dashboard/business/new", data={**BUSINESS_DATA, "slug": slug})

    assert response.status_code == 200
    assert db.session.scalar(select(Business)) is None


def test_create_business_rejects_taken_address(owner_client, other_service):
    response = owner_client.post("/dashboard/business/new", data={**BUSINESS_DATA, "slug": "other-shop"})

    assert b"This address is already taken." in response.data


@pytest.mark.parametrize(
    ("hours", "message"),
    [
        ("18:00-09:00", b"Closing time must be after opening time."),
        ("09:00-13:00, 12:00-15:00", b"Opening hours on the same day cannot overlap."),
        ("nine to five", b"Write hours like 09:00-13:00, 15:00-19:00."),
        ("09:15-12:00", b"Use times on the hour or half hour, up to 23:30."),
    ],
)
def test_create_business_rejects_bad_hours(owner_client, hours, message):
    response = owner_client.post("/dashboard/business/new", data={**BUSINESS_DATA, "hours-0": hours})

    assert message in response.data
    assert db.session.scalar(select(Business)) is None


def test_create_business_requires_opening_hours(owner_client):
    empty_week = {f"hours-{weekday}": "" for weekday in range(7)}

    response = owner_client.post("/dashboard/business/new", data={**BUSINESS_DATA, **empty_week})

    assert b"Add opening hours for at least one day." in response.data


def test_editing_business_replaces_its_hours(owner_client, business):
    owner_client.post("/dashboard/business/edit", data={**BUSINESS_DATA, "slug": "north-side"})

    assert business.open_weekdays == [0, 2, 4]
    assert len(business.opening_hours) == 4


def test_create_business_rejects_unknown_timezone(owner_client):
    response = owner_client.post("/dashboard/business/new", data={**BUSINESS_DATA, "timezone": "Mars/Base"})

    assert response.status_code == 200
    assert db.session.scalar(select(Business)) is None


def test_create_service_stores_price_in_cents(owner_client, business):
    response = owner_client.post(
        "/dashboard/services/new",
        data={"name": "Beard trim", "duration_minutes": "20", "price": "12.50"},
    )

    assert response.status_code == 302
    service = db.session.scalar(select(Service))
    assert service.price_cents == 1250
    assert b"$12.50" in owner_client.get("/dashboard/").data


def test_toggle_hides_and_shows_a_service(owner_client, service):
    owner_client.post(f"/dashboard/services/{service.id}/toggle")
    assert service.is_active is False

    owner_client.post(f"/dashboard/services/{service.id}/toggle")
    assert service.is_active is True


def test_owner_cannot_touch_another_owners_service(owner_client, business, other_service):
    assert owner_client.get(f"/dashboard/services/{other_service.id}/edit").status_code == 404
    assert owner_client.post(f"/dashboard/services/{other_service.id}/toggle").status_code == 404
    assert other_service.is_active is True


def test_delete_asks_for_confirmation_first(owner_client, service):
    response = owner_client.get(f"/dashboard/services/{service.id}/delete")

    assert response.status_code == 200
    assert b"Delete Haircut?" in response.data
    assert db.session.get(Service, service.id) is not None


def test_delete_removes_the_service(owner_client, service):
    service_id = service.id

    response = owner_client.post(f"/dashboard/services/{service_id}/delete")

    assert response.status_code == 302
    assert db.session.get(Service, service_id) is None


def test_service_with_bookings_cannot_be_deleted(owner_client, service):
    start = datetime(2026, 10, 14, 13, 0)
    booking = Booking(
        business=service.business,
        service=service,
        customer_name="Sam Rivera",
        customer_email="sam@example.com",
        starts_at=start,
        ends_at=start + timedelta(minutes=30),
    )
    db.session.add(booking)
    db.session.commit()

    owner_client.post(f"/dashboard/services/{service.id}/delete")

    assert db.session.get(Service, service.id) is not None


def test_owner_cannot_delete_another_owners_service(owner_client, business, other_service):
    assert owner_client.post(f"/dashboard/services/{other_service.id}/delete").status_code == 404
    assert db.session.get(Service, other_service.id) is not None
