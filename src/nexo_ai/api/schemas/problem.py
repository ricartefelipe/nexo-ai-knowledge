"""RFC 9457 problem detail schema."""

from pydantic import BaseModel, ConfigDict, Field


class ProblemError(BaseModel):
    """One validation failure, without the rejected input value."""

    model_config = ConfigDict(extra="forbid")

    loc: list[str]
    msg: str
    type: str


class ProblemDetails(BaseModel):
    """Machine-readable HTTP error body."""

    model_config = ConfigDict(extra="forbid")

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str
    errors: list[ProblemError] | None = None
    correlation_id: str | None = Field(default=None)
