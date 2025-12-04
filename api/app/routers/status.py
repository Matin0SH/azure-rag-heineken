"""
Status Router - Check PDF and Job processing status
"""
from fastapi import APIRouter, Depends, HTTPException, Path

from app.models.schemas import StatusResponse, JobStatusResponse, ErrorResponse, PDFListResponse, SummaryListResponse, QuestionListResponse
from app.services.pdf_service import pdf_service
from app.services.summarization_service import summarization_service
from app.services.question_generation_service import question_generation_service
from app.utils.auth import validate_api_key

router = APIRouter()

@router.get(
    "/pdf-status/{pdf_id}",
    response_model=StatusResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "PDF not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get PDF processing status",
    description="Retrieve processing status for a specific PDF by ID"
)
async def get_pdf_status(
    pdf_id: str = Path(..., description="Unique PDF identifier"),
    _: bool = Depends(validate_api_key)
):
    """
    Get the current processing status of a PDF.

    Returns information from the PDF registry table including:
    - Processing status (pending/processing/completed/failed)
    - Upload date
    - Processed date (if completed)
    - Error message (if failed)

    Args:
        pdf_id: Unique identifier returned from the ingest endpoint

    Returns:
        StatusResponse with PDF processing details
    """
    result = pdf_service.get_pdf_status(pdf_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"PDF with ID '{pdf_id}' not found"
        )

    return StatusResponse(**result)


@router.get(
    "/job-status/{run_id}",
    response_model=JobStatusResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Job run not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Get Databricks job run status",
    description="Retrieve status of a Databricks job run by run ID"
)
async def get_job_status(
    run_id: int = Path(..., description="Databricks job run ID"),
    _: bool = Depends(validate_api_key)
):
    """
    Get the current status of a Databricks job run.

    Returns detailed job execution information including:
    - Current state
    - Lifecycle state
    - Result state
    - Start/end times
    - Run page URL

    Args:
        run_id: Job run ID returned from the ingest endpoint

    Returns:
        JobStatusResponse with job execution details
    """
    result = pdf_service.get_job_status(run_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Job run with ID '{run_id}' not found"
        )

    # Extract relevant fields from Databricks response
    job_data = {
        "job_run_id": run_id,
        "state": result.get("state", {}).get("state_message", "unknown"),
        "life_cycle_state": result.get("state", {}).get("life_cycle_state", "unknown"),
        "result_state": result.get("state", {}).get("result_state"),
        "start_time": result.get("start_time"),
        "end_time": result.get("end_time"),
        "run_page_url": result.get("run_page_url", "")
    }

    return JobStatusResponse(**job_data)


@router.get(
    "/pdfs",
    response_model=PDFListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="List all PDFs",
    description="Get list of all PDFs from Databricks registry"
)
async def list_pdfs(
    _: bool = Depends(validate_api_key)
):
    """
    List all PDFs from the registry table.

    Returns:
        PDFListResponse with list of all PDFs and their status
    """
    result = pdf_service.list_pdfs()
    return PDFListResponse(**result)


@router.get(
    "/summaries",
    response_model=SummaryListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="List all summaries",
    description="Get list of all summaries from Databricks"
)
async def list_summaries(
    _: bool = Depends(validate_api_key)
):
    """
    List all summaries from the document_summaries table.

    Returns:
        SummaryListResponse with list of all summaries
    """
    result = summarization_service.list_summaries()
    return SummaryListResponse(**result)


@router.get(
    "/questions",
    response_model=QuestionListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="List all question sets",
    description="Get list of all generated question sets from Databricks"
)
async def list_questions(
    _: bool = Depends(validate_api_key)
):
    """
    List all question sets from the operator_questions table.

    Returns:
        QuestionListResponse with list of all question sets
    """
    result = question_generation_service.list_questions()
    return QuestionListResponse(**result)
