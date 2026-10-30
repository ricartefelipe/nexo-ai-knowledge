"""Checks whether an answer is actually backed by the fragments it was given.

Similarity found a fragment; that does not make the answer true. The check is lexical and
deliberately simple: every `[n]` citation must point to a returned fragment, at least one
citation must exist, and the cited fragments must share content with the answer. It never
upgrades an answer — it can only withhold the `supported` label.
"""

import re
import unicodedata
from collections.abc import Sequence

from nexo_ai.domain.retrieval import SourceReference, SupportStatus

_CITATION = re.compile(r"\[(\d+)\]")
_WORD = re.compile(r"\w+", re.UNICODE)
_MIN_SHARED_TERMS = 3
_MIN_TERM_LENGTH = 4


def assess_support(text: str, references: Sequence[SourceReference]) -> SupportStatus:
    """Classify an answer against the fragments handed to the model."""

    if not references:
        return SupportStatus.NO_SOURCES
    cited = {int(match) for match in _CITATION.findall(text)}
    if not cited or any(index < 1 or index > len(references) for index in cited):
        return SupportStatus.UNSUPPORTED
    answer_terms = _terms(text)
    cited_terms: set[str] = set()
    for index in cited:
        cited_terms |= _terms(references[index - 1].content)
    if len(answer_terms & cited_terms) < _MIN_SHARED_TERMS:
        return SupportStatus.UNSUPPORTED
    return SupportStatus.SUPPORTED


def _terms(text: str) -> set[str]:
    folded = "".join(
        character
        for character in unicodedata.normalize("NFKD", text.lower())
        if not unicodedata.combining(character)
    )
    return {
        token
        for token in _WORD.findall(folded)
        if len(token) >= _MIN_TERM_LENGTH and not token.isdigit()
    }
