"""HTTP schemas for grounded questions."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    """One natural-language question."""

    model_config = ConfigDict(extra="forbid")

    question: str


class ReferenceResponse(BaseModel):
    """Indexed fragment returned with an answer so the caller can check the source."""

    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    filename: str
    position: int
    content: str
    distance: float = Field(ge=0)


class QueryResponse(BaseModel):
    """Answer and the fragments that were close enough to use."""

    model_config = ConfigDict(extra="forbid")

    answer: str
    grounded: bool
    references: list[ReferenceResponse]
