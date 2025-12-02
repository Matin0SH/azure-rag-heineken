"""
Question Generation Service - Business logic for generating training questions
"""
from typing import Dict, Any
from fastapi import HTTPException

from app.services.databricks_client import databricks_client
from app.config.settings import settings

class QuestionGenerationService:
    """Service for handling question generation operations"""

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
        print(f"[DEBUG] Validating PDF for questions: {pdf_id}")

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
    def check_questions_exist(pdf_id: str) -> bool:
        """
        Check if questions already exist for this PDF

        Args:
            pdf_id: PDF identifier

        Returns:
            True if questions exist, False otherwise
        """
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.sql import StatementState

        w = WorkspaceClient(
            host=settings.DATABRICKS_HOST,
            token=settings.DATABRICKS_TOKEN
        )

        query = f"""
        SELECT questions_id
        FROM {settings.CATALOG_NAME}.`{settings.SCHEMA_NAME}`.operator_questions
        WHERE pdf_id = '{pdf_id}'
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
            print(f"Warning: Could not check existing questions - {e}")

        return False

    @staticmethod
    def trigger_question_generation(pdf_id: str) -> Dict[str, Any]:
        """
        Trigger question generation for a PDF

        Args:
            pdf_id: PDF identifier

        Returns:
            Question generation job information

        Raises:
            HTTPException: If validation fails or job trigger fails
        """
        # 1. Validate PDF exists and is processed
        pdf_info = QuestionGenerationService.validate_pdf_exists(pdf_id)

        if pdf_info["processing_status"] != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"PDF '{pdf_id}' is not fully processed yet. Current status: {pdf_info['processing_status']}"
            )

        # 2. Check if questions already exist (optional warning, not blocking)
        questions_exist = QuestionGenerationService.check_questions_exist(pdf_id)

        message = f"Generating training questions for '{pdf_info['pdf_name']}'"
        if questions_exist:
            message = f"Regenerating training questions for '{pdf_info['pdf_name']}' (existing questions will be replaced)"

        # 3. Trigger Databricks question generation job
        try:
            job_response = databricks_client.trigger_question_generation_job(pdf_id)
            job_run_id = job_response.get("run_id")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to trigger question generation job: {str(e)}"
            )

        return {
            "pdf_id": pdf_id,
            "pdf_name": pdf_info["pdf_name"],
            "job_run_id": job_run_id,
            "status": "processing",
            "message": message
        }


# Singleton instance
question_generation_service = QuestionGenerationService()
