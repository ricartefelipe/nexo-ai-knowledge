"""Synchronous database engine and session factory."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from nexo_ai.config.settings import Settings


def create_db_engine(settings: Settings) -> Engine:
    """Create a pooled engine. Connections are opened lazily on checkout."""

    return create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.db_connect_timeout},
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a session factory that keeps loaded attributes after commit."""

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
