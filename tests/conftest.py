import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


@pytest.fixture(scope="session")
def test_engine():
    test_url = os.getenv("TEST_DATABASE_URL", "").strip()
    if not test_url:
        pytest.skip("Set TEST_DATABASE_URL to a separate test database.")

    from app.config import settings

    if make_url(test_url) == make_url(settings.database_url):
        raise pytest.UsageError("TEST_DATABASE_URL must not match DATABASE_URL.")

    engine = create_engine(test_url, pool_pre_ping=True, pool_size=2, max_overflow=1)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture(autouse=True)
def require_test_database(test_engine):
    return test_engine
