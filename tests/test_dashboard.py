from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import select

from librardos.extensions import db
from librardos.models import Booking, Business, Service, User

USER_EMAIL = "owner@example.com"
USER_PASSWORD = "correct-horse"

BUSINESS_DATA = {
    "name": "North Side Barbers",
    "slug": "north-side",
    "opens_at": "09:00",
    "closes_at": "18:00",
    "open_weekdays": ["0", "2", "4"],
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
    assert business.open_days == "024"
    assert business.timezone == "America/New_York"
    assert business.opens_at == time(9, 0)


@pytest.mark.parametrize("slug", ["No Spaces", "ab", "trailing-", "émoji"])
def test_create_business_rejects_bad_addresses(owner_client, slug):
    response = owner_client.post("/dashboard/business/new", data={**BUSINESS_DATA, "slug": slug})

    assert response.status_code == 200
    assert db.session.scalar(select(Business)) is None


def test_create_business_rejects_taken_address(owner_client, other_service):
    response = owner_client.post("/dashboard/business/new", data={**BUSINESS_DATA, "slug": "other-shop"})

    assert b"This address is already taken." in response.data


def test_create_business_rejects_closing_before_opening(owner_client):
    response = owner_client.post(
        "/dashboard/business/new",
        data={**BUSINESS_DATA, "opens_at": "18:00", "closes_at": "09:00"},
    )

    assert b"Closing time must be after opening time." in response.data


def test_create_business_requires_an_open_day(owner_client):
    data = {key: value for key, value in BUSINESS_DATA.items() if key != "open_weekdays"}

    response = owner_client.post("/dashboard/business/new", data=data)

    assert b"Pick at least one day." in response.data


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
