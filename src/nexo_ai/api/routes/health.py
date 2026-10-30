"""Liveness and readiness routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from nexo_ai.api.dependencies.health import get_capabilities, get_readiness_probe
from nexo_ai.api.schemas.health import LivenessResponse, ReadinessResponse
from nexo_ai.api.schemas.problem import ProblemDetails
from nexo_ai.infrastructure.persistence.health import Capabilities, ReadinessProbe

router = APIRouter(tags=["health"])


@router.get(
    "/health/live",
    response_model=LivenessResponse,
    summary="Verifica se o processo está ativo",
)
def read_liveness() -> LivenessResponse:
    """Report process liveness without contacting the database."""

    return LivenessResponse(status="ok")


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    summary="Verifica se as dependências críticas estão disponíveis",
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ProblemDetails,
            "description": "O banco de dados ou a extensão vector não está disponível.",
        }
    },
)
def read_readiness(
    probe: Annotated[ReadinessProbe, Depends(get_readiness_probe)],
    capabilities: Annotated[Capabilities, Depends(get_capabilities)],
) -> ReadinessResponse:
    """Report whether PostgreSQL and pgvector can serve the current API."""

    report = probe.check()
    if not report.ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=report.detail)
    return ReadinessResponse(
        status="ready",
        database="ok",
        embedding_provider="configured" if capabilities.embedding_provider else "not_configured",
        completion_provider="configured" if capabilities.completion_provider else "not_configured",
        embedding_model=capabilities.embedding_model,
    )
