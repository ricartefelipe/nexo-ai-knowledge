"""Natural-language questions over indexed documents."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from nexo_ai.api.dependencies.queries import get_answer_question
from nexo_ai.api.schemas.problem import ProblemDetails
from nexo_ai.api.schemas.queries import QueryRequest, QueryResponse, ReferenceResponse
from nexo_ai.application.retrieve import AnswerQuestion
from nexo_ai.domain.documents import DocumentError
from nexo_ai.domain.retrieval import Answer

router = APIRouter(prefix="/api/v1", tags=["queries"])


@router.post(
    "/queries",
    response_model=QueryResponse,
    responses={status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ProblemDetails}},
)
def create_query(
    body: QueryRequest,
    answer_question: Annotated[AnswerQuestion, Depends(get_answer_question)],
) -> QueryResponse:
    """Answer a question from indexed fragments and return those fragments."""

    try:
        answer = answer_question.execute(body.question)
    except DocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.message,
        ) from None
    return _response(answer)


def _response(answer: Answer) -> QueryResponse:
    return QueryResponse(
        answer=answer.text,
        grounded=answer.grounded,
        support=answer.support.value,
        sources_found=answer.sources_found,
        references=[
            ReferenceResponse(
                document_id=source.document_id,
                filename=source.filename,
                position=source.position,
                content=source.content,
                distance=source.distance,
            )
            for source in answer.references
        ],
    )
