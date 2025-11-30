"""
PDF Service - Business logic for PDF ingestion
"""
import uuid
from typing import Dict, Any, Optional
from fastapi import UploadFile, HTTPException

from app.services.databricks_client import databricks_client, sanitize_filename
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

        # Use sanitized name consistently for lookup/upload/job
        original_name = file.filename
        pdf_name = sanitize_filename(original_name)

        # pdf_name IS the identifier - no unique ID needed
        pdf_id = pdf_name

        # Check if PDF with same name already exists
        existing = databricks_client.check_pdf_exists(pdf_name)

        if existing:
            # Cleanup existing PDF data
            print(f"PDF '{pdf_name}' already exists. Cleaning up old data...")
            try:
                databricks_client.cleanup_existing_pdf(pdf_name)
                print(f"Successfully cleaned up old data for '{pdf_name}'")
            except Exception as e:
                print(f"Warning during cleanup: {e}")
                # Continue anyway - we'll create new data

        # Read file content
        file_content = await file.read()

        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > settings.MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=413,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
            )

        # Upload to Databricks Volume using Files API (same as Streamlit app)
        try:
            import requests

            volume_path = f"/Volumes/{settings.CATALOG_NAME}/{settings.SCHEMA_NAME}/{settings.VOLUME_RAW_PDFS}/{pdf_name}"
            upload_url = f"{settings.DATABRICKS_HOST}/api/2.0/fs/files{volume_path}"

            headers = {
                "Authorization": f"Bearer {settings.DATABRICKS_TOKEN}",
                "Connection": "close"  # Disable keep-alive to prevent SSL issues
            }

            # PUT request automatically overwrites existing file
            response = requests.put(
                upload_url,
                headers=headers,
                data=file_content,
                timeout=300
            )

            if response.status_code not in (200, 201, 204):
                raise HTTPException(
                    status_code=500,
                    detail=f"Upload failed: {response.status_code} - {response.text}"
                )

        except requests.exceptions.RequestException as e:
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

        # Build response message
        if existing:
            message = f"PDF '{pdf_name}' re-uploaded. Old data cleaned up, processing started"
        else:
            message = f"PDF '{pdf_name}' uploaded and processing started"

        return {
            "pdf_id": pdf_name,  # pdf_id = pdf_name now
            "pdf_name": pdf_name,
            "job_run_id": job_run_id,
            "status": "processing",
            "message": message
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
