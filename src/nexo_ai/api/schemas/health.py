"""HTTP schemas for health responses."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class LivenessResponse(BaseModel):
    """Process liveness. This check does not touch external dependencies."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    """Readiness of the dependencies required to serve the current API."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready"]
