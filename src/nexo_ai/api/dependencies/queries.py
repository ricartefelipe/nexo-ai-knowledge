"""Query dependencies."""

from starlette.requests import Request

from nexo_ai.application.retrieve import AnswerQuestion


def get_answer_question(request: Request) -> AnswerQuestion:
    """Return the query use case stored by the composition root."""

    answer_question: AnswerQuestion = request.app.state.answer_question
    return answer_question
