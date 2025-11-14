from __future__ import annotations

"""Database helpers (engine + session factory)."""
# @tag:backend,models

# --- Imports -----------------------------------------------------------------
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


# --- ORM base -----------------------------------------------------------------
class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


def _ensure_parent_directory(database_path: Path) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)


# --- Engine + session factories ---------------------------------------------
_engine = None
_session_factory: sessionmaker | None = None


def get_engine():
    """Return a module-level SQLite engine (created lazily)."""

    global _engine
    if _engine is None:
        settings = get_settings()
        db_path = Path(settings.database_path)
        _ensure_parent_directory(db_path)
        connect_args = {"check_same_thread": False}
        _engine = create_engine(
            f"sqlite:///{db_path.as_posix()}",
            future=True,
            echo=settings.environment == "local",
            connect_args=connect_args,
        )
    return _engine


def get_sessionmaker():
    """Return a cached session factory bound to the shared engine."""

    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _session_factory


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session suitable for FastAPI dependencies."""

    session_factory = get_sessionmaker()
    session: Session = session_factory()
    try:
        yield session
    finally:
        session.close()


def reset_db_state() -> None:
    """Utility for tests to drop cached engines/session factories."""

    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
