"""API credential check. Active whenever API_AUTH_TOKEN is configured."""

import secrets

from fastapi import HTTPException, status
from starlette.requests import Request

from nexo_ai.config.settings import Settings

_BEARER = "bearer "


def require_api_token(request: Request) -> None:
    """Reject the request unless it carries the configured token.

    Accepts `Authorization: Bearer <token>` or `X-Api-Key: <token>`. With no token configured
    (local profile) the check is a no-op; the production profile cannot start without one.
    """

    settings: Settings = request.app.state.settings
    if not settings.api_auth_enabled:
        return
    presented = _presented_token(request)
    if presented is None or not secrets.compare_digest(presented, settings.api_auth_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial ausente ou inválida.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _presented_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith(_BEARER):
        return authorization[len(_BEARER) :].strip()
    api_key = request.headers.get("x-api-key")
    if api_key is not None and api_key.strip() != "":
        return api_key.strip()
    return None
