import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (register tables)
from app.database import get_session
from app.main import app


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture()
def client(session, monkeypatch):
    # Avoid real YouTube calls when songs are approved in tests.
    async def fake_resolve(artist: str, title: str) -> str | None:
        return "test-video-id"

    monkeypatch.setattr("app.services.youtube.resolve_video_id", fake_resolve)

    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def host_client(client):
    """Client with an authenticated host session cookie."""
    resp = client.post("/auth/session", json={"display_name": "DJ Test"})
    assert resp.status_code == 201
    return client


@pytest.fixture()
def party(host_client):
    resp = host_client.post("/party", json={"name": "Testparty"})
    assert resp.status_code == 201
    return resp.json()
