"""
Question Generation Router
"""
from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import QuestionGenerationRequest, QuestionGenerationResponse, ErrorResponse
from app.services.question_generation_service import question_generation_service
from app.utils.auth import validate_api_key

router = APIRouter()

@router.post(
    "/generate-questions",
    response_model=QuestionGenerationResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or PDF not ready"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "PDF not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Generate training questions",
    description="Trigger question generation job for a processed PDF"
)
async def generate_questions(
    request: QuestionGenerationRequest,
    _: bool = Depends(validate_api_key)
):
    """
    Generate training questions for a processed PDF.

    The endpoint will:
    1. Validate that the PDF exists and is fully processed
    2. Check if questions already exist (will regenerate if so)
    3. Trigger the question generation job
    4. Return job run ID for tracking

    Args:
        request: QuestionGenerationRequest with pdf_id

    Returns:
        QuestionGenerationResponse with job_run_id and status
    """
    result = question_generation_service.trigger_question_generation(
        pdf_id=request.pdf_id
    )
    return QuestionGenerationResponse(**result)
