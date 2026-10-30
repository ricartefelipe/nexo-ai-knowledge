"""Application composition root."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import Depends, FastAPI

from nexo_ai import __version__
from nexo_ai.api.dependencies.auth import require_api_token
from nexo_ai.api.handlers.errors import register_exception_handlers
from nexo_ai.api.middleware.correlation import RequestContextMiddleware
from nexo_ai.api.routes.documents import router as document_router
from nexo_ai.api.routes.health import router as health_router
from nexo_ai.api.routes.interface import router as interface_router
from nexo_ai.api.routes.queries import router as query_router
from nexo_ai.application.ingest import IngestDocument
from nexo_ai.application.retrieve import AnswerQuestion
from nexo_ai.config.logging import configure_logging
from nexo_ai.config.settings import Settings, get_settings
from nexo_ai.infrastructure.completions.openai import build_completion_client
from nexo_ai.infrastructure.embeddings.openai import EMBEDDING_DIMENSIONS, build_embedding_client
from nexo_ai.infrastructure.extraction.text import extract_document
from nexo_ai.infrastructure.persistence.database import create_db_engine, create_session_factory
from nexo_ai.infrastructure.persistence.documents import SqlDocumentRepository
from nexo_ai.infrastructure.persistence.health import Capabilities, DatabaseReadinessProbe

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
        app.state.capabilities = Capabilities(
            embedding_provider=resolved.embedding_api_key != "",
            completion_provider=resolved.completion_api_key != "",
            embedding_model=resolved.embedding_model,
        )
        repository = SqlDocumentRepository(
            session_factory, embedding_model=resolved.embedding_model
        )
        app.state.document_repository = repository
        embeddings = build_embedding_client(resolved)
        app.state.ingest_document = IngestDocument(
            repository=repository,
            embeddings=embeddings,
            extract=extract_document,
            chunk_size=resolved.document_chunk_size,
            chunk_overlap=resolved.document_chunk_overlap,
            max_bytes=resolved.document_max_bytes,
            dimensions=EMBEDDING_DIMENSIONS,
            embedding_model=resolved.embedding_model,
        )
        app.state.answer_question = AnswerQuestion(
            search=repository,
            embeddings=embeddings,
            completion=build_completion_client(resolved),
            max_distance=resolved.query_max_distance,
            match_limit=resolved.query_match_limit,
            max_chars=resolved.query_max_chars,
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
            "Plataforma de conhecimento corporativo. A interface local e a API verificam "
            "a saúde do processo, ingerem PDF, Markdown e TXT e respondem perguntas com "
            "as fontes encontradas. Ingestão e consulta exigem provedor; a subida do "
            "processo não exige. Com API_AUTH_TOKEN configurado (obrigatório em "
            "produção), documentos, consultas e interface exigem a credencial."
        ),
    )
    app.state.settings = resolved
    register_exception_handlers(app)
    app.add_middleware(RequestContextMiddleware)
    protected = [Depends(require_api_token)]
    app.include_router(interface_router, dependencies=protected)
    app.include_router(health_router)
    app.include_router(document_router, dependencies=protected)
    app.include_router(query_router, dependencies=protected)
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
