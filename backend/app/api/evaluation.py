"""On-demand retrieval and generation evaluation helpers."""

from fastapi import APIRouter, Depends

from backend.app.core.dependencies import check_rate_limit, get_current_user
from backend.app.evaluation.generation import evaluate_generation
from backend.app.evaluation.retrieval import evaluate_retrieval
from backend.app.models.schemas import (
    GenerationEvaluationRequest,
    GenerationEvaluationResponse,
    RetrievalEvaluationRequest,
    RetrievalEvaluationResponse,
)


router = APIRouter(prefix="/evaluation", tags=["evaluation"], dependencies=[Depends(check_rate_limit)])


@router.post("/retrieval", response_model=RetrievalEvaluationResponse)
def retrieval_evaluation(
    payload: RetrievalEvaluationRequest,
    _user: dict = Depends(get_current_user),
) -> dict:
    return evaluate_retrieval(payload.relevant_ids, payload.retrieved_ids, payload.k)


@router.post("/generation", response_model=GenerationEvaluationResponse)
def generation_evaluation(
    payload: GenerationEvaluationRequest,
    _user: dict = Depends(get_current_user),
) -> dict:
    return evaluate_generation(
        question=payload.question,
        answer=payload.answer,
        context=payload.context,
        expected_answer=payload.expected_answer,
        cited_ids=payload.cited_ids,
        available_ids=payload.available_ids,
    )
