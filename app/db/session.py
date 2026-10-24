"""Database engine and connectivity checks."""

import logging

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings

logger = logging.getLogger(__name__)


def create_db_engine(settings: Settings) -> Engine:
    # create_engine does not open a connection, so the app starts even when
    # the database is down. Health checks report that state instead.
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
    )


def check_connection(engine: Engine) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.warning("Database connection check failed", exc_info=True)
        return False
    return True
