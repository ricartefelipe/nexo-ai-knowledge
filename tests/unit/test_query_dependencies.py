"""Composition dependency for grounded questions."""

from typing import cast

from starlette.requests import Request

from nexo_ai.api.dependencies.queries import get_answer_question


class _State:
    def __init__(self, answer_question: object) -> None:
        self.answer_question = answer_question


class _App:
    def __init__(self, state: _State) -> None:
        self.state = state


class _Request:
    def __init__(self, app: _App) -> None:
        self.app = app


def test_query_dependency_returns_the_use_case_stored_on_the_application() -> None:
    answer_question = object()
    request = cast(Request, _Request(_App(_State(answer_question))))
    assert get_answer_question(request) is answer_question
