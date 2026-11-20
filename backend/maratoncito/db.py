"""Database configuration and SQLAlchemy declarative base."""

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    return os.environ.get("MARATONCITO_DATABASE_URL", "sqlite:///./maratoncito.db")


def make_engine(url: str | None = None) -> Engine:
    url = url or database_url()
    if url.startswith("sqlite:////"):
        # Container entrypoint creates /data; local paths must be managed by the caller.
        path = Path(url.removeprefix("sqlite:////"))
        if path.is_absolute() and path.parent == Path("/data"):
            path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, pool_pre_ping=True)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine
