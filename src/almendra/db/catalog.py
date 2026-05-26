"""Engine / session plumbing for the catalog DB.

SQLite is the default backend; the same SQLModel schema runs on Postgres by
passing a different URL. Foreign-key enforcement is turned on for SQLite (off by
default there) so the junction tables keep referential integrity.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

# Import models so SQLModel.metadata is populated before create_all().
from almendra.db import models  # noqa: F401
from almendra.paths import data_dir


def default_db_path() -> Path:
    """``data/catalog.db`` under the repo root (honours ALMENDRA_ROOT)."""
    return data_dir() / "catalog.db"


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _record) -> None:
    """Enforce foreign keys on SQLite (no-op on other backends)."""
    module = type(dbapi_connection).__module__
    if "sqlite3" in module:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_engine(db_path: str | Path | None = None, *, echo: bool = False) -> Engine:
    """Create an engine for a SQLite file (or ``:memory:`` if ``db_path`` is ':memory:')."""
    if db_path == ":memory:":
        url = "sqlite://"
    else:
        path = Path(db_path) if db_path is not None else default_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path}"
    return create_engine(url, echo=echo)


def init_db(engine: Engine) -> None:
    """Create every catalog table that does not yet exist."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session(engine: Engine) -> Iterator[Session]:
    """A transactional session: commit on success, roll back on error."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
