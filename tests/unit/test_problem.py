"""Problem detail construction."""

from nexo_ai.api.handlers.errors import build_problem
from nexo_ai.api.schemas.problem import ProblemError


def test_problem_document_uses_the_http_reason_phrase() -> None:
    problem = build_problem(
        status_code=503,
        detail="O banco de dados está indisponível.",
        instance="/health/ready",
        correlation_id="abc123",
    )
    dumped = problem.model_dump(exclude_none=True)
    assert dumped == {
        "type": "about:blank",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "O banco de dados está indisponível.",
        "instance": "/health/ready",
        "correlation_id": "abc123",
    }


def test_unknown_status_code_uses_a_generic_title() -> None:
    problem = build_problem(status_code=999, detail="Falha.", instance="/health/live")
    assert problem.title == "Error"
    assert problem.status == 999


def test_validation_problem_keeps_only_location_message_and_type() -> None:
    problem = build_problem(
        status_code=422,
        detail="A requisição é inválida.",
        instance="/health/live",
        errors=[ProblemError(loc=["path", "item_id"], msg="invalid", type="int_parsing")],
    )
    error = problem.model_dump(exclude_none=True)["errors"][0]
    assert set(error) == {"loc", "msg", "type"}
