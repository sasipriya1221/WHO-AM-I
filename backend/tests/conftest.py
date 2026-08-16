import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, engine as app_engine
from app import models
from app.main import app
from app.services.dna import engine as dna_engine
from app.services.evidence import semantic
from tests.provider_spies import RecordingProviderSpy


@pytest.fixture(autouse=True)
def reset_app_database():
    """Keep API tests deterministic across repeated local and CI runs."""
    Base.metadata.drop_all(bind=app_engine)
    Base.metadata.create_all(bind=app_engine)
    yield


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    with Session() as session:
        yield session


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def provider_spy(monkeypatch):
    spy = RecordingProviderSpy()
    monkeypatch.setattr(dna_engine, "get_ai_provider", lambda: spy)
    monkeypatch.setattr(semantic, "get_ai_provider", lambda: spy)
    return spy
