"""Shared fixtures. Integration fixtures use the rag_test database on the Compose PostgreSQL."""

import os
import re
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://rag:rag@localhost:5433/rag_test"
)
ADMIN_DATABASE_URL = os.environ.get(
    "ADMIN_DATABASE_URL", "postgresql+psycopg://rag:rag@localhost:5433/rag"
)


def _create_test_database_if_missing() -> None:
    database = make_url(TEST_DATABASE_URL).database or ""
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        raise RuntimeError(f"Unsafe test database name: {database!r}")
    engine = create_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            exists = connection.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database}
            )
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{database}"'))
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def migrated_database() -> str:
    _create_test_database_if_missing()
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")
    return TEST_DATABASE_URL


@pytest.fixture
def clean_database(migrated_database: str) -> Iterator[str]:
    engine = create_engine(migrated_database)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE documents CASCADE"))
    yield migrated_database
    engine.dispose()


@pytest.fixture
def make_client(clean_database: str) -> Iterator[Callable[..., TestClient]]:
    clients: list[TestClient] = []

    def _make(database_url: str | None = None, **overrides: object) -> TestClient:
        settings = Settings(
            _env_file=None,
            database_url=database_url or clean_database,
            **overrides,
        )
        client = TestClient(create_app(settings))
        clients.append(client)
        return client

    yield _make
    for client in clients:
        client.close()
        # The app creates its engine eagerly; release its pooled connections.
        client.app.state.engine.dispose()


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    return make_client()
