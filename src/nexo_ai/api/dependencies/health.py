"""Database readiness dependency."""

from starlette.requests import Request

from nexo_ai.infrastructure.persistence.health import ReadinessProbe


def get_readiness_probe(request: Request) -> ReadinessProbe:
    """Return the probe stored by the composition root."""

    probe: ReadinessProbe = request.app.state.readiness_probe
    return probe
