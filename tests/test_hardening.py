from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import inspect
import io
import secrets
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core import rate_limit
from app.database import get_db
from app.models import Customer, LoginCode, Property, PropertyImage, Query
from app.routers.admin import images as image_router
from app.schemas.customer import CustomerInput
from app.schemas.property import PropertyInput, SoldInput
from app.schemas.query import QueryCreate
from app.services import auth_service, customer_service, image_service, property_service, query_service


@pytest.fixture(autouse=True)
def clear_limiter_state():
    rate_limit._attempts.clear()
    rate_limit._windows.clear()
    yield
    rate_limit._attempts.clear()
    rate_limit._windows.clear()


def test_all_admin_routes_require_auth():
    from app.main import app

    exempt = {"/api/admin/auth/request-code", "/api/admin/auth/verify-code"}
    checked = 0
    # FastAPI can retain included routers lazily, so enumerate the final schema.
    schema = app.openapi()
    for route_path, path_item in schema["paths"].items():
        if not route_path.startswith("/api/admin"):
            continue
        for method, operation in path_item.items():
            if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            if route_path in exempt:
                continue
            assert operation.get("security"), (method.upper(), route_path)
            checked += 1
    assert checked > 0


def test_api_docs_default_off_only_in_production(monkeypatch):
    from app.config import Settings

    monkeypatch.delenv("ENABLE_DOCS", raising=False)
    assert Settings(environment="production").enable_docs is False
    assert Settings(environment="local").enable_docs is True
    monkeypatch.setenv("ENABLE_DOCS", "true")
    assert Settings(environment="production").enable_docs is True


def test_login_code_attempts_expiry_single_use_and_non_admin(db, monkeypatch):
    monkeypatch.setattr(
        auth_service, "settings", SimpleNamespace(jwt_secret="test-secret-" * 4, admin_email="admin@example.test")
    )
    sender = patch.object(auth_service, "send_login_code")
    with sender as send:
        assert auth_service.request_code(db, "not-admin@example.test") is False
        assert send.call_count == 0
        assert db.scalar(select(func.count(LoginCode.id))) == 0

        now = datetime.now(timezone.utc)
        expired = LoginCode(code_hash=auth_service._hash("12345678"), expires_at=now - timedelta(seconds=1), used=False)
        db.add(expired)
        db.commit()
        assert auth_service.verify_code(db, "12345678") is False

        exhausted = LoginCode(
            code_hash=auth_service._hash("12345678"), expires_at=now + timedelta(minutes=10), used=False
        )
        db.add(exhausted)
        db.commit()
        for _ in range(5):
            assert auth_service.verify_code(db, "87654321") is False
        db.refresh(exhausted)
        assert exhausted.used is True
        assert auth_service.verify_code(db, "12345678") is False

        valid = LoginCode(code_hash=auth_service._hash("87654321"), expires_at=now + timedelta(minutes=10), used=False)
        db.add(valid)
        db.commit()
        assert auth_service.verify_code(db, "87654321") is True
        assert auth_service.verify_code(db, "87654321") is False


def test_login_request_limits_and_failed_email_preserves_old_code(db, monkeypatch):
    monkeypatch.setattr(
        auth_service, "settings", SimpleNamespace(jwt_secret="test-secret-" * 4, admin_email="admin@example.test")
    )
    db.execute(delete(LoginCode))
    db.commit()
    captured = []

    def accept(_email, code):
        captured.append(code)

    with patch.object(auth_service, "send_login_code", side_effect=accept):
        assert auth_service.request_code(db, "admin@example.test") is True
        previous_code = captured[-1]
        with patch.object(auth_service, "send_login_code", side_effect=RuntimeError("email unavailable")):
            assert auth_service.request_code(db, "admin@example.test") is False
        assert auth_service.verify_code(db, previous_code) is True

    db.execute(delete(LoginCode))
    db.commit()
    captured.clear()
    with patch.object(auth_service, "send_login_code", side_effect=accept):
        for _ in range(3):
            assert auth_service.request_code(db, "admin@example.test") is True
        sent_before = len(captured)
        assert auth_service.request_code(db, "admin@example.test") is False
        assert len(captured) == sent_before

    db.execute(delete(LoginCode))
    db.commit()
    now = datetime.now(timezone.utc)
    db.add_all(
        [
            LoginCode(code_hash="unused", expires_at=now + timedelta(minutes=1), created_at=now - timedelta(hours=2))
            for _ in range(10)
        ]
    )
    db.commit()
    with patch.object(auth_service, "send_login_code") as send:
        assert auth_service.request_code(db, "admin@example.test") is False
        assert send.call_count == 0


def test_limiter_returns_429_and_cleans_expired_ip(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(rate_limit, "monotonic", lambda: clock[0])
    for _ in range(5):
        rate_limit.enforce_rate_limit("visitor-a", scope="test", limit=5, window_seconds=60, message="limited")
    with pytest.raises(HTTPException) as error:
        rate_limit.enforce_rate_limit("visitor-a", scope="test", limit=5, window_seconds=60, message="limited")
    assert error.value.status_code == 429
    clock[0] = 161.0
    rate_limit.enforce_rate_limit("visitor-b", scope="test", limit=5, window_seconds=60, message="limited")
    assert ("test", "visitor-a") not in rate_limit._attempts


def test_public_enquiry_rate_limit_returns_429(db):
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    ip = f"192.0.2.{secrets.randbelow(200) + 1}"
    client = TestClient(app, client=(ip, 12345), raise_server_exceptions=False)
    body = {"name": "Rate Test", "phone": "9876543210", "whatsapp_number": "9876543210", "message": "test"}
    try:
        responses = [client.post("/api/public/queries", json=body) for _ in range(6)]
    finally:
        app.dependency_overrides.pop(get_db, None)
    assert [response.status_code for response in responses[:5]] == [200] * 5
    assert responses[5].status_code == 429


def test_property_validation_generated_areas_and_public_privacy(db):
    with pytest.raises(ValidationError):
        PropertyInput(
            title="Plot",
            property_type="plot",
            address="Road",
            length=10,
            width=20,
            price=100,
            building_details={"bedrooms": 0, "kitchens": 0, "bathrooms": 0, "building_area": 0},
        )
    with pytest.raises(ValidationError):
        PropertyInput(title="House", property_type="house", address="Road", length=10, width=20, price=100)
    with pytest.raises(ValidationError):
        PropertyInput(
            title="Unsafe",
            property_type="plot",
            address="Road",
            length=10,
            width=20,
            price=100,
            maps_url="javascript:alert(1)",
        )

    data = PropertyInput(
        title="  Garden plot  ",
        property_type="house",
        address="  Main Road  ",
        length=10,
        width=20,
        price=100,
        maps_url=" https://maps.google.com/?q=here ",
        building_details={
            "bedrooms": 2,
            "kitchens": 1,
            "bathrooms": 1,
            "building_area": 100,
            "garden_area": 25,
            "parking_area": 10,
        },
    )
    prop = property_service.save_property(db, data)
    assert prop.area == 200
    assert prop.building_details.total_area == 135
    assert prop.title == "Garden plot" and prop.address == "Main Road"
    db.add(
        PropertyImage(
            property_id=prop.id,
            image_url="https://res.cloudinary.com/test/image.jpg",
            public_id="private-id",
            display_order=0,
        )
    )
    db.commit()
    db.refresh(prop)
    public = property_service.property_dict(prop, public=True)
    assert not {
        "buyer_id",
        "buyer_name",
        "buyer_phone",
        "buyer_whatsapp_number",
        "buyer_email",
        "sale_price",
        "public_id",
    } & set(public)
    assert "public_id" not in public["images"][0]


def test_text_trimming_and_readable_sold_validation():
    assert CustomerInput(name=" Name ", phone=" 9876543210 ", whatsapp_number=" 9876543210 ").name == "Name"
    query = QueryCreate(name=" Visitor ", phone=" 9876543210 ", whatsapp_number=" 9876543210 ", message=" hello ")
    assert (query.name, query.message) == ("Visitor", "hello")
    with pytest.raises(ValidationError):
        QueryCreate(name="   ", phone="9876543210", whatsapp_number="9876543210")
    with pytest.raises(ValidationError) as bad_email:
        SoldInput(buyer_name="Buyer", buyer_phone="9876543", buyer_whatsapp_number="9876543", buyer_email="nope")
    assert "Enter a valid buyer email" in str(bad_email.value)
    from app.routers.admin.properties import PropertyStatus

    with pytest.raises(ValidationError) as bad_phone:
        PropertyStatus(status="sold", buyer_name="Buyer", buyer_phone="123", buyer_whatsapp_number="123")
    assert "Enter a valid buyer phone number" in str(bad_phone.value)


def test_customer_reuse_keeps_first_name_and_fills_email(db):
    first = customer_service.find_or_create(db, "First Name", "9876543210", "9876543210")
    db.commit()
    repeated = customer_service.find_or_create(db, "Different Name", "9876543210", "9876543210", "buyer@example.test")
    db.commit()
    assert repeated.id == first.id
    assert repeated.name == "First Name"
    assert repeated.email == "buyer@example.test"
    assert db.scalar(select(func.count(Customer.id)).where(Customer.phone == "+919876543210")) == 1


def test_simultaneous_customer_creation_reuses_unique_phone(test_engine):
    phone = f"8{secrets.randbelow(1_000_000_000):09d}"
    barrier = Barrier(2)

    def create(name):
        with Session(test_engine, expire_on_commit=False) as session:
            barrier.wait(timeout=10)
            customer = customer_service.find_or_create(session, name, phone, phone)
            session.commit()
            return customer.id

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(create, ("Concurrent A", "Concurrent B")))
        assert ids[0] == ids[1]
    finally:
        with Session(test_engine) as cleanup:
            cleanup.execute(delete(Customer).where(Customer.phone == "+91" + phone))
            cleanup.commit()


def test_query_resolve_and_reopen_are_idempotent(db):
    customer = customer_service.find_or_create(db, "Query User", "9876543211", "9876543211")
    item = Query(customer=customer, status="new", message="test")
    db.add(item)
    db.commit()
    query_service.set_query_status(item, True)
    db.commit()
    resolved_at = item.resolved_at
    query_service.set_query_status(item, True)
    db.commit()
    assert item.status == "resolved" and item.resolved_at == resolved_at
    query_service.set_query_status(item, False)
    db.commit()
    assert item.status == "new" and item.resolved_at is None
    query_service.set_query_status(item, False)
    db.commit()
    assert item.status == "new" and item.resolved_at is None


def test_image_upload_validation_ordering_and_missing_property(db, monkeypatch):
    monkeypatch.setattr(image_service, "settings", SimpleNamespace(max_image_bytes=5 * 1024 * 1024))
    monkeypatch.setattr(image_router, "settings", SimpleNamespace(max_image_bytes=5 * 1024 * 1024, max_image_count=10))
    with pytest.raises(ValueError, match="JPG, PNG, or WebP"):
        image_service.upload_image(b"image", "image/gif")
    with pytest.raises(ValueError, match="size limit"):
        image_service.upload_image(b"x" * (5 * 1024 * 1024 + 1), "image/jpeg")

    prop = Property(title="Image test", property_type="plot", address="test", length=1, width=1, price=1)
    db.add(prop)
    db.commit()
    counter = [0]

    def fake_upload(_data, _mime):
        counter[0] += 1
        return {"secure_url": f"https://images.test/{counter[0]}", "public_id": f"test-{counter[0]}"}

    monkeypatch.setattr(image_router, "upload_image", fake_upload)
    monkeypatch.setattr(image_router, "delete_image", lambda _public_id: None)
    uploads = [SimpleNamespace(file=io.BytesIO(b"a"), content_type="image/jpeg") for _ in range(3)]
    result = image_router.upload_images(prop.id, uploads, db)
    assert [image["display_order"] for image in result] == [0, 1, 2]
    db.delete(db.get(PropertyImage, result[1]["id"]))
    db.commit()
    later = image_router.upload_images(prop.id, [SimpleNamespace(file=io.BytesIO(b"b"), content_type="image/jpeg")], db)
    assert later[0]["display_order"] == 3

    with pytest.raises(HTTPException) as error:
        image_router.reorder_images(prop.id + 999999, image_router.OrderInput(image_ids=[]), db)
    assert error.value.status_code == 404
    assert not inspect.iscoroutinefunction(image_router.upload_images)


def test_property_delete_commits_before_best_effort_cloud_cleanup(db, monkeypatch):
    prop = Property(title="Delete test", property_type="plot", address="test", length=1, width=1, price=1)
    db.add(prop)
    db.flush()
    db.add(PropertyImage(property_id=prop.id, image_url="https://img.test/a", public_id="test-delete", display_order=0))
    db.commit()
    prop = property_service.get_property(db, prop.id)
    observed = []

    def cloud_delete(_public_id):
        observed.append(db.get(Property, prop.id) is None)
        raise RuntimeError("simulated Cloudinary outage")

    monkeypatch.setattr(property_service, "delete_image", cloud_delete)
    property_service.delete_property(db, prop)
    assert observed == [True]
    assert db.get(Property, prop.id) is None
