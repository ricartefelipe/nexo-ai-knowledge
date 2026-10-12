"""Application composition root."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from nexo_ai import __version__
from nexo_ai.api.handlers.errors import register_exception_handlers
from nexo_ai.api.middleware.correlation import RequestContextMiddleware
from nexo_ai.api.routes.documents import router as document_router
from nexo_ai.api.routes.health import router as health_router
from nexo_ai.application.ingest import IngestDocument
from nexo_ai.config.logging import configure_logging
from nexo_ai.config.settings import Settings, get_settings
from nexo_ai.infrastructure.embeddings.openai import EMBEDDING_DIMENSIONS, build_embedding_client
from nexo_ai.infrastructure.extraction.text import extract_document
from nexo_ai.infrastructure.persistence.database import create_db_engine, create_session_factory
from nexo_ai.infrastructure.persistence.documents import SqlDocumentRepository
from nexo_ai.infrastructure.persistence.health import DatabaseReadinessProbe

logger = structlog.get_logger()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the ASGI application. Passing settings avoids reading the process environment."""

    resolved = settings if settings is not None else get_settings()
    configure_logging(resolved.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_db_engine(resolved)
        app.state.engine = engine
        session_factory = create_session_factory(engine)
        app.state.session_factory = session_factory
        app.state.readiness_probe = DatabaseReadinessProbe(engine)
        repository = SqlDocumentRepository(session_factory)
        app.state.document_repository = repository
        app.state.ingest_document = IngestDocument(
            repository=repository,
            embeddings=build_embedding_client(resolved),
            extract=extract_document,
            chunk_size=resolved.document_chunk_size,
            chunk_overlap=resolved.document_chunk_overlap,
            max_bytes=resolved.document_max_bytes,
            dimensions=EMBEDDING_DIMENSIONS,
        )
        logger.info(
            "application_started",
            component="nexo_ai.app",
            operation="startup",
            result="ok",
            app_env=resolved.app_env.value,
        )
        try:
            yield
        finally:
            engine.dispose()
            logger.info(
                "application_stopped",
                component="nexo_ai.app",
                operation="shutdown",
                result="ok",
            )

    app = FastAPI(
        title="Nexo AI",
        version=__version__,
        lifespan=lifespan,
        description=(
            "Plataforma de conhecimento corporativo. A API verifica a saúde do processo "
            "e ingere PDF, Markdown e TXT. A ingestão exige um provedor de embeddings; "
            "a subida do processo não exige. Não há autenticação: o uso previsto é local."
        ),
    )
    app.state.settings = resolved
    register_exception_handlers(app)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health_router)
    app.include_router(document_router)
    return app


def main() -> None:
    """Run the HTTP server using process settings."""

    settings = get_settings()
    configure_logging(settings.log_level)
    uvicorn.run(
        "nexo_ai.main:create_app",
        factory=True,
        host=settings.app_host,
        port=settings.app_port,
        access_log=False,
        log_level=settings.log_level.lower(),
    )
