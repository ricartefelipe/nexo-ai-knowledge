"""Composition dependencies for ingestion."""

from typing import cast

from starlette.requests import Request

from nexo_ai.api.dependencies.documents import (
    get_document_max_bytes,
    get_document_repository,
    get_ingest_document,
)
from nexo_ai.config.settings import Settings
from tests.conftest import build_settings


class _State:
    def __init__(self, ingest_document: object, repository: object, settings: Settings) -> None:
        self.ingest_document = ingest_document
        self.document_repository = repository
        self.settings = settings


class _App:
    def __init__(self, state: _State) -> None:
        self.state = state


class _Request:
    def __init__(self, app: _App) -> None:
        self.app = app


def test_dependencies_return_objects_stored_on_the_application() -> None:
    ingest_document = object()
    repository = object()
    settings = build_settings()
    request = _Request(_App(_State(ingest_document, repository, settings)))
    typed = cast(Request, request)
    assert get_ingest_document(typed) is ingest_document
    assert get_document_repository(typed) is repository
    assert get_document_max_bytes(typed) == settings.document_max_bytes
