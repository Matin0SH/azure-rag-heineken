"""
Summarization Router
"""
from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import SummarizationRequest, SummarizationResponse, ErrorResponse
from app.services.summarization_service import summarization_service
from app.utils.auth import validate_api_key

router = APIRouter()

@router.post(
    "/summarize",
    response_model=SummarizationResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request or PDF not ready"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "PDF not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Generate PDF summary",
    description="Trigger summarization job for a processed PDF"
)
async def summarize_pdf(
    request: SummarizationRequest,
    _: bool = Depends(validate_api_key)
):
    """
    Generate a summary for a processed PDF.

    The endpoint will:
    1. Validate that the PDF exists and is fully processed
    2. Check if summary already exists (will regenerate if so)
    3. Trigger the summarization job
    4. Return job run ID for tracking

    Args:
        request: SummarizationRequest with pdf_id and summary_type

    Returns:
        SummarizationResponse with job_run_id and status
    """
    result = summarization_service.trigger_summarization(
        pdf_id=request.pdf_id,
        summary_type=request.summary_type.value
    )
    return SummarizationResponse(**result)
