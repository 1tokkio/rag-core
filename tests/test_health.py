from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.api.deps import get_engine
from app.core.config import Settings
from app.main import create_app


def _client_with_engine(engine) -> TestClient:
    app = create_app(Settings(_env_file=None))
    app.dependency_overrides[get_engine] = lambda: engine
    return TestClient(app)


def test_health_returns_200_when_database_answers():
    engine = create_engine("sqlite://")
    client = _client_with_engine(engine)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unreachable():
    # Port 1 on localhost has no listener, so the connection is refused.
    engine = create_engine(
        "postgresql+psycopg://rag:rag@127.0.0.1:1/rag",
        connect_args={"connect_timeout": 1},
    )
    client = _client_with_engine(engine)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "down"}
