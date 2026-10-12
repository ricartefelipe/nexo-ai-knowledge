"""Request correlation and access logging."""

import re
import time
from uuid import uuid4

import structlog
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CORRELATION_ID_HEADER = "X-Request-ID"
_CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
logger = structlog.get_logger()


def resolve_correlation_id(header_value: str | None) -> str:
    """Accept a safe caller-supplied id, or generate a new one."""

    if header_value is not None and _CORRELATION_ID_PATTERN.fullmatch(header_value):
        return header_value
    return str(uuid4())


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


class RequestContextMiddleware:
    """Bind a correlation id to the request, the response, and the logs."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        correlation_id = resolve_correlation_id(request.headers.get(CORRELATION_ID_HEADER))
        state = scope.setdefault("state", {})
        if isinstance(state, dict):
            state["correlation_id"] = correlation_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_correlation(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                headers = [
                    (name, value)
                    for name, value in message.get("headers", [])
                    if name.lower() != b"x-request-id"
                ]
                headers.append((b"x-request-id", correlation_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation)
        except Exception as exc:
            logger.error(
                "request_failed",
                component="nexo_ai.api",
                operation="http_request",
                result="error",
                error_type=type(exc).__name__,
                http_method=request.method,
                http_path=request.url.path,
                duration_ms=_elapsed_ms(started),
            )
            raise
        else:
            logger.info(
                "request_completed",
                component="nexo_ai.api",
                operation="http_request",
                result="ok" if status_code < 400 else "error",
                http_method=request.method,
                http_path=request.url.path,
                http_status=status_code,
                duration_ms=_elapsed_ms(started),
            )
        finally:
            structlog.contextvars.clear_contextvars()
