"""
PDF Ingestion Router
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException

from app.models.schemas import IngestResponse, ErrorResponse
from app.services.pdf_service import pdf_service
from app.utils.auth import validate_api_key

router = APIRouter()

@router.post(
    "/ingest-pdf",
    response_model=IngestResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        413: {"model": ErrorResponse, "description": "File too large"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="Ingest PDF for processing",
    description="Upload a PDF file to trigger ingestion pipeline"
)
async def ingest_pdf(
    file: UploadFile = File(..., description="PDF file to ingest"),
    _: bool = Depends(validate_api_key)
):
    """
    Upload and process a PDF file through the RAG pipeline.

    The endpoint will:
    1. Validate the PDF file
    2. Upload it to Databricks Volume
    3. Trigger the ingestion job
    4. Return processing status

    Returns:
        IngestResponse with pdf_id, job_run_id, and status
    """
    result = await pdf_service.ingest_pdf(file)
    return IngestResponse(**result)
