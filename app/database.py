"""Database engine and session dependency.

SQLite via SQLModel in Phase 1. ``get_session`` is a FastAPI dependency that
yields a short-lived session per request.
"""

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# ``check_same_thread`` must be disabled so the SQLite connection can be used
# across FastAPI's threadpool. Harmless for non-SQLite URLs (Phase 2 Postgres).
_connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)


def create_db_and_tables() -> None:
    """Create all tables from the SQLModel metadata.

    Useful for tests / quick local bootstrapping. Production schema changes go
    through Alembic migrations.
    """
    # Import models so they are registered on SQLModel.metadata before create.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
