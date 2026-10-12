"""Translate exceptions into RFC 9457 problem details."""

from http import HTTPStatus

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from nexo_ai.api.schemas.problem import ProblemDetails, ProblemError

PROBLEM_JSON = "application/problem+json"
logger = structlog.get_logger()


def build_problem(
    *,
    status_code: int,
    detail: str,
    instance: str,
    errors: list[ProblemError] | None = None,
    correlation_id: str | None = None,
) -> ProblemDetails:
    """Build a problem document that does not include stack traces or request input."""

    try:
        title = HTTPStatus(status_code).phrase
    except ValueError:
        title = "Error"
    return ProblemDetails(
        title=title,
        status=status_code,
        detail=detail,
        instance=instance,
        errors=errors,
        correlation_id=correlation_id,
    )


def problem_response(problem: ProblemDetails) -> JSONResponse:
    """Return the problem document with the RFC 9457 media type."""

    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(exclude_none=True),
        media_type=PROBLEM_JSON,
    )


def _correlation_id(request: Request) -> str | None:
    value = getattr(request.state, "correlation_id", None)
    if isinstance(value, str):
        return value
    context_value = structlog.contextvars.get_contextvars().get("correlation_id")
    if isinstance(context_value, str):
        return context_value
    return None


def _validation_errors(exc: RequestValidationError) -> list[ProblemError]:
    problems: list[ProblemError] = []
    for error in exc.errors():
        location = error.get("loc", ())
        problems.append(
            ProblemError(
                loc=[str(part) for part in location],
                msg=str(error.get("msg", "")),
                type=str(error.get("type", "")),
            )
        )
    return problems


def register_exception_handlers(app: FastAPI) -> None:
    """Register handlers that never return a traceback to the client."""

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        problem = build_problem(
            status_code=422,
            detail="A requisição é inválida.",
            instance=request.url.path,
            errors=_validation_errors(exc),
            correlation_id=_correlation_id(request),
        )
        return problem_response(problem)

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        raw_detail: object = exc.detail
        if isinstance(raw_detail, str):
            detail = raw_detail
        else:
            detail = "A requisição não pôde ser processada."
        problem = build_problem(
            status_code=exc.status_code,
            detail=detail,
            instance=request.url.path,
            correlation_id=_correlation_id(request),
        )
        return problem_response(problem)

    @app.exception_handler(Exception)
    async def handle_unexpected_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            component="nexo_ai.api",
            operation="handle_exception",
            result="error",
            error_type=type(exc).__name__,
        )
        problem = build_problem(
            status_code=500,
            detail="Ocorreu um erro interno.",
            instance=request.url.path,
            correlation_id=_correlation_id(request),
        )
        return problem_response(problem)
