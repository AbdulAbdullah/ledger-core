from collections.abc import Iterator

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine
from app.models import Account, LedgerEntry, LedgerTransaction


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        session.query(LedgerEntry).delete()
        session.query(LedgerTransaction).delete()
        session.query(Account).delete()
        session.commit()
    yield
    with SessionLocal() as session:
        session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(delete(table))
        session.commit()


@pytest.fixture
def db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
