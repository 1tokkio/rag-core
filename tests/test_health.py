from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

UNREACHABLE_DATABASE_URL = "postgresql+psycopg://rag:rag@127.0.0.1:1/rag"


def test_liveness_returns_200_even_when_database_is_unreachable():
    settings = Settings(_env_file=None, database_url=UNREACHABLE_DATABASE_URL)
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_200_when_database_answers(make_client):
    client = make_client()

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_readiness_returns_503_when_database_is_unreachable():
    settings = Settings(
        _env_file=None,
        database_url=UNREACHABLE_DATABASE_URL,
        db_connect_timeout_seconds=1,
    )
    client = TestClient(create_app(settings))

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "DATABASE_UNAVAILABLE",
            "message": "Database is not ready",
            "fields": {},
        }
    }
