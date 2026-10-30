"""Grounded question answering."""

from uuid import uuid4

import pytest

from nexo_ai.application.retrieve import AnswerQuestion
from nexo_ai.domain.documents import EmbeddingNotConfigured
from nexo_ai.domain.retrieval import RetrievalError, SourceReference, SupportStatus
from nexo_ai.infrastructure.completions.openai import UnconfiguredCompletionClient
from nexo_ai.infrastructure.embeddings.openai import UnconfiguredEmbeddingClient
from tests.fakes import (
    ExplodingCompletionClient,
    MemoryChunkSearch,
    ScriptedCompletionClient,
    ScriptedEmbeddingClient,
)


def _reference(
    distance: float, content: str = "O prazo de entrega é de 30 dias corridos."
) -> SourceReference:
    return SourceReference(
        document_id=uuid4(),
        filename="contrato.md",
        position=0,
        content=content,
        distance=distance,
    )


def _answer(
    search: MemoryChunkSearch,
    embeddings: ScriptedEmbeddingClient | UnconfiguredEmbeddingClient,
    completion: ScriptedCompletionClient | UnconfiguredCompletionClient | ExplodingCompletionClient,
) -> AnswerQuestion:
    return AnswerQuestion(
        search=search,
        embeddings=embeddings,
        completion=completion,
        max_distance=0.5,
        match_limit=2,
        max_chars=20,
        dimensions=4,
    )


def test_answer_cites_only_close_sources() -> None:
    close = _reference(0.1)
    far = _reference(0.9, content="outro fato")
    search = MemoryChunkSearch([close, far])
    embeddings = ScriptedEmbeddingClient(dimensions=4)
    completion = ScriptedCompletionClient()
    result = _answer(search, embeddings, completion).execute("  qual o prazo?  ")
    assert result.grounded is True
    assert result.support is SupportStatus.SUPPORTED
    assert result.text == "O prazo de entrega é de 30 dias corridos [1]."
    assert result.references == (close,)
    assert search.calls[0][1:] == (2, 0.5)
    assert completion.calls[0][0] == ""
    assert completion.calls[1][0] == "qual o prazo?"
    assert completion.calls[1][1] == (close,)


def test_distant_sources_do_not_call_the_language_model() -> None:
    search = MemoryChunkSearch([_reference(0.8)])
    completion = ScriptedCompletionClient()
    result = _answer(search, ScriptedEmbeddingClient(dimensions=4), completion).execute("prazo")
    assert result.grounded is False
    assert result.support is SupportStatus.NO_SOURCES
    assert result.references == ()
    assert result.text == "As fontes indexadas não respondem a essa pergunta."


def test_answer_without_citation_or_overlap_is_returned_as_unsupported() -> None:
    close = _reference(0.1)
    search = MemoryChunkSearch([close])
    embeddings = ScriptedEmbeddingClient(dimensions=4)

    uncited = _answer(search, embeddings, ScriptedCompletionClient("O prazo é de 30 dias."))
    result = uncited.execute("qual o prazo?")
    assert result.support is SupportStatus.UNSUPPORTED
    assert result.grounded is False
    assert result.sources_found is True
    assert result.references == (close,)

    invented = _answer(
        search,
        embeddings,
        ScriptedCompletionClient("A garantia cobre defeitos por cinco anos [1]."),
    )
    assert invented.execute("qual o prazo?").support is SupportStatus.UNSUPPORTED

    bad_index = _answer(
        search,
        embeddings,
        ScriptedCompletionClient("O prazo de entrega é de 30 dias corridos [2]."),
    )
    assert bad_index.execute("qual o prazo?").support is SupportStatus.UNSUPPORTED


def test_invalid_questions_are_rejected_before_search() -> None:
    search = MemoryChunkSearch([])
    use_case = _answer(search, ScriptedEmbeddingClient(dimensions=4), ScriptedCompletionClient())
    with pytest.raises(RetrievalError, match="vazia"):
        use_case.execute("   ")
    with pytest.raises(RetrievalError, match="tamanho"):
        use_case.execute("x" * 21)
    assert search.calls == []


def test_missing_providers_do_not_search() -> None:
    search = MemoryChunkSearch([_reference(0.1)])
    with pytest.raises(RetrievalError, match="linguagem não está configurado"):
        _answer(
            search, ScriptedEmbeddingClient(dimensions=4), UnconfiguredCompletionClient()
        ).execute("prazo")
    with pytest.raises(EmbeddingNotConfigured, match="embeddings não está configurado"):
        _answer(search, UnconfiguredEmbeddingClient(), ScriptedCompletionClient()).execute("prazo")
    assert search.calls == []


def test_unexpected_vector_shape_is_rejected() -> None:
    search = MemoryChunkSearch([_reference(0.1)])
    use_case = _answer(search, ScriptedEmbeddingClient(dimensions=3), ScriptedCompletionClient())
    with pytest.raises(RetrievalError, match="dimensão"):
        use_case.execute("prazo")
    assert search.calls == []


def test_empty_completion_is_rejected() -> None:
    search = MemoryChunkSearch([_reference(0.1)])
    use_case = _answer(
        search, ScriptedEmbeddingClient(dimensions=4), ScriptedCompletionClient("  ")
    )
    with pytest.raises(RetrievalError, match="resposta vazia"):
        use_case.execute("prazo")


def test_unexpected_completion_error_hides_the_message() -> None:
    search = MemoryChunkSearch([_reference(0.1)])
    use_case = _answer(search, ScriptedEmbeddingClient(dimensions=4), ExplodingCompletionClient())
    with pytest.raises(RetrievalError, match="A consulta falhou") as caught:
        use_case.execute("prazo")
    assert "super-secret" not in str(caught.value)
