"""
PDF Service - Business logic for PDF ingestion
"""
import uuid
from typing import Dict, Any, Optional
from fastapi import UploadFile, HTTPException

from app.services.databricks_client import databricks_client
from app.config.settings import settings

class PDFService:
    """Service for handling PDF ingestion operations"""

    @staticmethod
    def validate_pdf(file: UploadFile) -> None:
        """
        Validate uploaded PDF file

        Args:
            file: Uploaded file

        Raises:
            HTTPException: If validation fails
        """
        # Check file extension
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed"
            )

        # Check content type
        if file.content_type != 'application/pdf':
            raise HTTPException(
                status_code=400,
                detail="Invalid content type. Expected application/pdf"
            )

    @staticmethod
    async def ingest_pdf(file: UploadFile) -> Dict[str, Any]:
        """
        Process PDF ingestion

        Args:
            file: Uploaded PDF file

        Returns:
            Ingestion result with pdf_id and job_run_id
        """
        # Validate file
        PDFService.validate_pdf(file)

        # Generate unique PDF ID
        pdf_id = str(uuid.uuid4())
        pdf_name = file.filename

        # Read file content
        file_content = await file.read()

        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
            )

        # Save file temporarily and upload to Databricks Volume
        try:
            import tempfile
            import os
            from databricks.sdk import WorkspaceClient

            # Initialize Databricks SDK client
            w = WorkspaceClient(
                host=settings.DATABRICKS_HOST,
                token=settings.DATABRICKS_TOKEN
            )

            # Upload to volume using SDK
            volume_path = f"/Volumes/{settings.CATALOG_NAME}/{settings.SCHEMA_NAME}/{settings.VOLUME_RAW_PDFS}/{pdf_name}"

            # Write file using Databricks SDK
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(file_content)
                tmp_path = tmp_file.name

            try:
                # Upload using SDK files API
                with open(tmp_path, 'rb') as f:
                    w.files.upload(volume_path, f, overwrite=True)
            finally:
                # Clean up temp file
                os.unlink(tmp_path)

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload file to Databricks: {str(e)}"
            )

        # Trigger Databricks job
        try:
            job_response = databricks_client.trigger_job(pdf_name, pdf_id)
            job_run_id = job_response.get("run_id")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to trigger Databricks job: {str(e)}"
            )

        return {
            "pdf_id": pdf_id,
            "pdf_name": pdf_name,
            "job_run_id": job_run_id,
            "status": "processing",
            "message": f"PDF '{pdf_name}' uploaded and processing started"
        }

    @staticmethod
    def get_pdf_status(pdf_id: str) -> Optional[Dict[str, Any]]:
        """
        Get PDF processing status from registry table

        Args:
            pdf_id: Unique PDF identifier

        Returns:
            PDF status information or None if not found
        """
        query = f"""
        SELECT
            pdf_id,
            pdf_name,
            file_path,
            upload_date,
            processing_status,
            processed_date,
            error_message
        FROM {settings.CATALOG_NAME}.{settings.SCHEMA_NAME}.{settings.TABLE_REGISTRY}
        WHERE pdf_id = '{pdf_id}'
        """

        try:
            result = databricks_client.query_sql_warehouse(query)
            # Parse result (implementation depends on response format)
            # This is a simplified version
            return result
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to query PDF status: {str(e)}"
            )

    @staticmethod
    def get_job_status(run_id: int) -> Dict[str, Any]:
        """
        Get Databricks job run status

        Args:
            run_id: Job run ID

        Returns:
            Job run status information
        """
        try:
            return databricks_client.get_job_run_status(run_id)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get job status: {str(e)}"
            )


# Singleton instance
pdf_service = PDFService()
