from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.schemas.retrieval import RetrievalRequest, RetrievalResponse
from persistence.database import get_session
from services.retrieval import retrieve_context

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.post("/preview", response_model=RetrievalResponse)
def preview_retrieval(
    payload: RetrievalRequest, session: SessionDependency
) -> RetrievalResponse:
    return retrieve_context(
        session,
        payload.datasource_id,
        payload.question,
        top_k=payload.top_k,
    )
