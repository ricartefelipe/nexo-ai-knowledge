"""Database readiness dependency."""

from starlette.requests import Request

from nexo_ai.infrastructure.persistence.health import Capabilities, ReadinessProbe


def get_readiness_probe(request: Request) -> ReadinessProbe:
    """Return the probe stored by the composition root."""

    probe: ReadinessProbe = request.app.state.readiness_probe
    return probe


def get_capabilities(request: Request) -> Capabilities:
    """Return the capability flags stored by the composition root."""
    capabilities: Capabilities = request.app.state.capabilities
    return capabilities
