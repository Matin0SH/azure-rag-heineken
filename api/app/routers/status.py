"""
Status Router - Check PDF and Job processing status
"""
from fastapi import APIRouter, Depends, HTTPException, Path

from app.models.schemas import StatusResponse, JobStatusResponse, ErrorResponse
from app.services.pdf_service import pdf_service
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
