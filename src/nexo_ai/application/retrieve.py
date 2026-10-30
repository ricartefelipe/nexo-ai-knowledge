"""Answer a question from indexed document fragments."""

import time
from collections.abc import Sequence
from typing import Protocol

import structlog

from nexo_ai.application.embeddings import EmbeddingClient
from nexo_ai.domain.documents import DocumentError
from nexo_ai.domain.retrieval import (
    Answer,
    CompletionFailed,
    RetrievalError,
    SourceReference,
    SupportStatus,
)
from nexo_ai.domain.support import assess_support

logger = structlog.get_logger()

_NO_SOURCE = "As fontes indexadas não respondem a essa pergunta."


class ChunkSearch(Protocol):
    """Nearest indexed fragments for one query vector."""

    def nearest_chunks(
        self,
        embedding: Sequence[float],
        *,
        limit: int,
        max_distance: float,
    ) -> Sequence[SourceReference]:
        """Return fragments no farther than `max_distance`, closest first."""


class CompletionClient(Protocol):
    """Write an answer constrained to the supplied sources."""

    def complete(self, *, question: str, references: Sequence[SourceReference]) -> str:
        """Return the answer text. An empty question and no references probes configuration."""


class AnswerQuestion:
    """Embed a question, search indexed fragments, and answer only from those fragments."""

    def __init__(
        self,
        search: ChunkSearch,
        embeddings: EmbeddingClient,
        completion: CompletionClient,
        *,
        max_distance: float,
        match_limit: int,
        max_chars: int,
        dimensions: int,
    ) -> None:
        self._search = search
        self._embeddings = embeddings
        self._completion = completion
        self._max_distance = max_distance
        self._match_limit = match_limit
        self._max_chars = max_chars
        self._dimensions = dimensions

    def execute(self, question: str) -> Answer:
        """Answer one question. Without close sources, no language model is called."""

        started = time.perf_counter()
        cleaned = question.strip()
        if cleaned == "":
            raise RetrievalError("A pergunta está vazia.")
        if len(cleaned) > self._max_chars:
            raise RetrievalError("A pergunta excede o tamanho máximo.")
        try:
            self._completion.complete(question="", references=())
            vectors = self._embeddings.embed([cleaned])
            if len(vectors) != 1 or len(vectors[0]) != self._dimensions:
                raise RetrievalError(
                    "O provedor de embeddings devolveu um vetor com dimensão inesperada."
                )
            matches = tuple(
                self._search.nearest_chunks(
                    vectors[0],
                    limit=self._match_limit,
                    max_distance=self._max_distance,
                )
            )
            if not matches:
                answer = Answer(text=_NO_SOURCE, support=SupportStatus.NO_SOURCES, references=())
                _log_answer(answer, started, result="no_sources")
                return answer
            text = self._completion.complete(question=cleaned, references=matches)
            if text.strip() == "":
                raise CompletionFailed("O provedor de linguagem devolveu uma resposta vazia.")
            support = assess_support(text, matches)
            answer = Answer(text=text.strip(), support=support, references=matches)
        except DocumentError as exc:
            _log_answer(None, started, result="error")
            raise exc
        except Exception as exc:
            _log_answer(None, started, result="error", error_type=type(exc).__name__)
            raise RetrievalError("A consulta falhou.") from None
        _log_answer(answer, started, result=answer.support.value)
        return answer


def _log_answer(
    answer: Answer | None,
    started: float,
    *,
    result: str,
    error_type: str | None = None,
) -> None:
    logger.info(
        "question_answered",
        component="nexo_ai.retrieval",
        operation="answer_question",
        result=result,
        reference_count=0 if answer is None else len(answer.references),
        grounded=False if answer is None else answer.grounded,
        duration_ms=round((time.perf_counter() - started) * 1000, 3),
        error_type=error_type,
    )
