"""The support check only withholds the `supported` label; it never invents backing."""

from uuid import uuid4

from nexo_ai.domain.retrieval import SourceReference, SupportStatus
from nexo_ai.domain.support import assess_support


def _reference(content: str) -> SourceReference:
    return SourceReference(
        document_id=uuid4(), filename="politica.md", position=0, content=content, distance=0.1
    )


def test_no_sources_means_no_support() -> None:
    assert assess_support("qualquer texto [1]", ()) is SupportStatus.NO_SOURCES


def test_cited_fragment_sharing_content_is_supported() -> None:
    source = _reference("O reembolso de despesas médicas exige nota fiscal original.")
    answer = "O reembolso de despesas médicas exige a nota fiscal original [1]."
    assert assess_support(answer, (source,)) is SupportStatus.SUPPORTED


def test_answer_without_citation_is_unsupported_even_when_sources_exist() -> None:
    source = _reference("O reembolso de despesas médicas exige nota fiscal original.")
    assert assess_support("O reembolso exige nota fiscal.", (source,)) is SupportStatus.UNSUPPORTED


def test_citation_out_of_range_or_without_overlap_is_unsupported() -> None:
    source = _reference("O reembolso de despesas médicas exige nota fiscal original.")
    assert (
        assess_support("Reembolso médico exige nota [2].", (source,)) is SupportStatus.UNSUPPORTED
    )
    assert (
        assess_support("A empresa fica em Lisboa desde 1990 [1].", (source,))
        is SupportStatus.UNSUPPORTED
    )


def test_accents_and_case_do_not_break_the_overlap() -> None:
    source = _reference("Férias coletivas são comunicadas com quinze dias de antecedência.")
    answer = "FERIAS COLETIVAS sao comunicadas com quinze dias de antecedencia [1]."
    assert assess_support(answer, (source,)) is SupportStatus.SUPPORTED
