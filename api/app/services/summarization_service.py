"""
Summarization Service - Business logic for PDF summarization
"""
from typing import Dict, Any
from fastapi import HTTPException

from app.services.databricks_client import databricks_client
from app.config.settings import settings

class SummarizationService:
    """Service for handling PDF summarization operations"""

    @staticmethod
    def validate_pdf_exists(pdf_id: str) -> Dict[str, Any]:
        """
        Validate that PDF exists in registry

        Args:
            pdf_id: PDF identifier

        Returns:
            PDF information from registry

        Raises:
            HTTPException: If PDF not found
        """
        print(f"[DEBUG] Validating PDF: {pdf_id}")
        print(f"[DEBUG] SQL_WAREHOUSE_ID: {settings.SQL_WAREHOUSE_ID}")
        print(f"[DEBUG] DATABRICKS_HOST: {settings.DATABRICKS_HOST}")

        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.sql import StatementState

        try:
            w = WorkspaceClient(
                host=settings.DATABRICKS_HOST,
                token=settings.DATABRICKS_TOKEN
            )
            print("[DEBUG] WorkspaceClient created successfully")
        except Exception as e:
            print(f"[ERROR] Failed to create WorkspaceClient: {e}")
            raise

        query = f"""
        SELECT pdf_id, pdf_name, processing_status
        FROM {settings.CATALOG_NAME}.`{settings.SCHEMA_NAME}`.{settings.TABLE_REGISTRY}
        WHERE pdf_id = '{pdf_id}'
        LIMIT 1
        """
        print(f"[DEBUG] Query: {query}")

        try:
            print("[DEBUG] Executing SQL statement...")
            statement = w.statement_execution.execute_statement(
                warehouse_id=settings.SQL_WAREHOUSE_ID,
                statement=query,
                wait_timeout="30s"
            )
            print(f"[DEBUG] Statement executed. State: {statement.status.state}")
            if hasattr(statement.status, 'error'):
                print(f"[DEBUG] Statement error: {statement.status.error}")

            if statement.status.state == StatementState.SUCCEEDED:
                print(f"[DEBUG] Result data: {statement.result}")
                if statement.result and statement.result.data_array:
                    row = statement.result.data_array[0]
                    print(f"[DEBUG] Found PDF: {row}")
                    return {
                        "pdf_id": row[0],
                        "pdf_name": row[1],
                        "processing_status": row[2]
                    }
                else:
                    print("[DEBUG] No data returned")
                    raise HTTPException(
                        status_code=404,
                        detail=f"PDF '{pdf_id}' not found in registry. Please ingest the PDF first."
                    )
            else:
                print(f"[DEBUG] Statement failed with state: {statement.status.state}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to query PDF registry. State: {statement.status.state}"
                )

        except HTTPException:
            raise
        except Exception as e:
            import traceback
            error_detail = f"Error checking PDF: {str(e)}\n{traceback.format_exc()}"
            print(error_detail)
            raise HTTPException(
                status_code=500,
                detail=f"Error checking PDF: {str(e)}"
            )

    @staticmethod
    def check_summary_exists(pdf_id: str, summary_type: str) -> bool:
        """
        Check if summary already exists

        Args:
            pdf_id: PDF identifier
            summary_type: Type of summary

        Returns:
            True if summary exists, False otherwise
        """
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.sql import StatementState

        w = WorkspaceClient(
            host=settings.DATABRICKS_HOST,
            token=settings.DATABRICKS_TOKEN
        )

        query = f"""
        SELECT summary_id
        FROM {settings.CATALOG_NAME}.`{settings.SCHEMA_NAME}`.document_summaries
        WHERE pdf_id = '{pdf_id}' AND summary_type = '{summary_type}'
        LIMIT 1
        """

        try:
            statement = w.statement_execution.execute_statement(
                warehouse_id=settings.SQL_WAREHOUSE_ID,
                statement=query,
                wait_timeout="30s"
            )

            if statement.status.state == StatementState.SUCCEEDED:
                return bool(statement.result and statement.result.data_array)

        except Exception as e:
            print(f"Warning: Could not check existing summary - {e}")

        return False

    @staticmethod
    def trigger_summarization(pdf_id: str, summary_type: str) -> Dict[str, Any]:
        """
        Trigger summarization for a PDF

        Args:
            pdf_id: PDF identifier
            summary_type: Type of summary ('technical' or 'operator')

        Returns:
            Summarization job information

        Raises:
            HTTPException: If validation fails or job trigger fails
        """
        # 1. Validate PDF exists and is processed
        pdf_info = SummarizationService.validate_pdf_exists(pdf_id)

        if pdf_info["processing_status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"PDF '{pdf_id}' is not fully processed yet. Current status: {pdf_info['processing_status']}"
            )

        # 2. Check if summary already exists (optional warning, not blocking)
        summary_exists = SummarizationService.check_summary_exists(pdf_id, summary_type)

        message = f"Generating {summary_type} summary for '{pdf_info['pdf_name']}'"
        if summary_exists:
            message = f"Regenerating {summary_type} summary for '{pdf_info['pdf_name']}' (existing summary will be replaced)"

        # 3. Trigger Databricks summarization job
        try:
            job_response = databricks_client.trigger_summarization_job(pdf_id, summary_type)
            job_run_id = job_response.get("run_id")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to trigger summarization job: {str(e)}"
            )

        return {
            "pdf_id": pdf_id,
            "pdf_name": pdf_info["pdf_name"],
            "summary_type": summary_type,
            "job_run_id": job_run_id,
            "status": "processing",
            "message": message
        }

    @staticmethod
    def list_summaries() -> Dict[str, Any]:
        """
        List all summaries from Databricks

        Returns:
            List of summaries
        """
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.sql import StatementState

        try:
            w = WorkspaceClient(
                host=settings.DATABRICKS_HOST,
                token=settings.DATABRICKS_TOKEN
            )

            query = f"""
            SELECT
                summary_id,
                pdf_id,
                pdf_name,
                summary_type,
                created_at
            FROM {settings.CATALOG_NAME}.`{settings.SCHEMA_NAME}`.document_summaries
            ORDER BY created_at DESC
            """

            statement = w.statement_execution.execute_statement(
                warehouse_id=settings.SQL_WAREHOUSE_ID,
                statement=query,
                wait_timeout="30s"
            )

            summaries = []
            if statement.status.state == StatementState.SUCCEEDED:
                if statement.result and statement.result.data_array:
                    for row in statement.result.data_array:
                        summaries.append({
                            "summary_id": row[0],
                            "pdf_id": row[1],
                            "pdf_name": row[2],
                            "summary_type": row[3],
                            "created_at": row[4]
                        })

            return {
                "summaries": summaries,
                "total": len(summaries)
            }

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list summaries: {str(e)}"
            )


# Singleton instance
summarization_service = SummarizationService()
