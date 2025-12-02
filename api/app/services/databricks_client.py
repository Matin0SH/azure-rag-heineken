"""
Databricks API Client Service
"""
import requests
from typing import Dict, Any, Optional
import uuid

from app.config.settings import settings
import hashlib

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent URL issues
    - Removes special characters
    - Limits length to 50 chars
    - Preserves extension
    """
    name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "pdf")

    # Remove special characters, keep alphanumeric, hyphens, underscores
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)

    # Limit length and add hash for uniqueness
    if len(safe_name) > 40:
        hash_suffix = hashlib.md5(filename.encode()).hexdigest()[:6]
        safe_name = f"{safe_name[:40]}_{hash_suffix}"

    return f"{safe_name}.{ext}"

class DatabricksClient:
    """Client for interacting with Databricks REST API"""

    def __init__(self):
        self.host = settings.DATABRICKS_HOST
        self.token = settings.DATABRICKS_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def trigger_job(self, pdf_name: str, pdf_id: str) -> Dict[str, Any]:
        """
        Trigger Databricks job for PDF ingestion

        Args:
            pdf_name: Original PDF filename
            pdf_id: Unique PDF identifier

        Returns:
            Job run information including run_id
        """
        url = f"{self.host}/api/2.1/jobs/run-now"

        payload = {
            "job_id": settings.INGEST_JOB_ID,
            "notebook_params": {
                "pdf_name": pdf_name,
                "pdf_id": pdf_id
            }
        }

        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def trigger_summarization_job(self, pdf_id: str, summary_type: str) -> Dict[str, Any]:
        """
        Trigger Databricks job for PDF summarization

        Args:
            pdf_id: PDF identifier
            summary_type: Type of summary ('technical' or 'operator')

        Returns:
            Job run information including run_id
        """
        url = f"{self.host}/api/2.1/jobs/run-now"

        payload = {
            "job_id": settings.SUMMARIZATION_JOB_ID,
            "notebook_params": {
                "pdf_id": pdf_id,
                "summary_type": summary_type
            }
        }

        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def trigger_question_generation_job(self, pdf_id: str) -> Dict[str, Any]:
        """
        Trigger Databricks job for question generation

        Args:
            pdf_id: PDF identifier

        Returns:
            Job run information including run_id
        """
        url = f"{self.host}/api/2.1/jobs/run-now"

        payload = {
            "job_id": settings.QUESTION_GENERATION_JOB_ID,
            "notebook_params": {
                "pdf_id": pdf_id
            }
        }

        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def get_job_run_status(self, run_id: int) -> Dict[str, Any]:
        """
        Get job run status

        Args:
            run_id: Databricks job run ID

        Returns:
            Job run status information
        """
        url = f"{self.host}/api/2.1/jobs/runs/get"
        params = {"run_id": run_id}

        response = requests.get(url, params=params, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def upload_to_volume(self, file_content: bytes, filename: str) -> str:
        """
        Upload file to Databricks Volume using Files API

        Args:
            file_content: PDF file content as bytes
            filename: Original filename

        Returns:
            Volume path
        """
        # Correct volume path format
        volume_path = f"/Volumes/{settings.CATALOG_NAME}/{settings.SCHEMA_NAME}/{settings.VOLUME_RAW_PDFS}/{filename}"

        # Use the correct Files API endpoint with proper parameters
        url = f"{self.host}/api/2.0/fs/files{volume_path}"

        headers = {
            "Authorization": f"Bearer {self.token}",
        }

        # Use PUT request with overwrite parameter
        response = requests.put(
            url,
            data=file_content,
            headers=headers,
            params={"overwrite": "true"}
        )

        # If 401, try alternative approach using dbfs
        if response.status_code == 401:
            # Fallback: Use workspace import API to write to volume
            return self._upload_via_workspace(file_content, filename)

        response.raise_for_status()

        return volume_path

    def _upload_via_workspace(self, file_content: bytes, filename: str) -> str:
        """
        Alternative upload method using workspace files API

        Args:
            file_content: PDF file content as bytes
            filename: Original filename

        Returns:
            Volume path
        """
        import base64

        volume_path = f"/Volumes/{settings.CATALOG_NAME}/{settings.SCHEMA_NAME}/{settings.VOLUME_RAW_PDFS}/{filename}"
        url = f"{self.host}/api/2.0/workspace/import"

        # Encode content to base64
        encoded_content = base64.b64encode(file_content).decode('utf-8')

        payload = {
            "path": volume_path,
            "content": encoded_content,
            "format": "AUTO",
            "overwrite": True
        }

        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()

        return volume_path

    def query_sql_warehouse(self, query: str) -> Dict[str, Any]:
        """
        Execute SQL query on Databricks SQL Warehouse

        Args:
            query: SQL query string

        Returns:
            Query results
        """
        url = f"{self.host}/api/2.0/sql/statements"

        payload = {
            "warehouse_id": settings.SQL_WAREHOUSE_ID,
            "statement": query,
            "wait_timeout": "30s"
        }

        response = requests.post(url, json=payload, headers=self.headers)
        response.raise_for_status()

        return response.json()

    def check_pdf_exists(self, pdf_name: str) -> bool:
        """
        Check if PDF with given name already exists by checking BOTH registry and volume

        Args:
            pdf_name: PDF filename to check (this IS the identifier now)

        Returns:
            True if exists, False otherwise
        """
        from databricks.sdk import WorkspaceClient
        from databricks.sdk.service.sql import StatementState

        w = WorkspaceClient(
            host=settings.DATABRICKS_HOST,
            token=settings.DATABRICKS_TOKEN
        )

        # Strategy 1: Check registry table (most reliable if job completed)
        if settings.SQL_WAREHOUSE_ID:
            query = f"""
            SELECT pdf_id
            FROM {settings.CATALOG_NAME}.{settings.SCHEMA_NAME}.{settings.TABLE_REGISTRY}
            WHERE pdf_name = '{pdf_name}'
            LIMIT 1
            """

            try:
                statement = w.statement_execution.execute_statement(
                    warehouse_id=settings.SQL_WAREHOUSE_ID,
                    statement=query,
                    wait_timeout="30s"
                )

                if statement.status.state == StatementState.SUCCEEDED and statement.result and statement.result.data_array:
                    print(f"Found existing PDF in registry: {pdf_name}")
                    return True

            except Exception as e:
                print(f"Error checking registry: {e}")

        # Strategy 2: Check if file exists in volume (backup check)
        try:
            volume_path = f"/Volumes/{settings.CATALOG_NAME}/{settings.SCHEMA_NAME}/{settings.VOLUME_RAW_PDFS}/{pdf_name}"
            file_info = w.files.get_status(volume_path)
            if file_info:
                print(f"Found existing PDF in volume: {pdf_name}")
                return True
        except Exception as e:
            # File doesn't exist - this is good
            pass

        return False

    def cleanup_existing_pdf(self, pdf_name: str) -> None:
        """
        Delete all data related to an existing PDF

        Args:
            pdf_name: PDF filename (this IS the identifier - no separate pdf_id anymore)
        """
        from databricks.sdk import WorkspaceClient

        w = WorkspaceClient(
            host=settings.DATABRICKS_HOST,
            token=settings.DATABRICKS_TOKEN
        )

        print(f"Cleaning up all data for PDF: {pdf_name}")

        # Execute cleanup queries - pdf_id = pdf_name now
        cleanup_queries = [
            # Delete chunks and embeddings
            f"DELETE FROM {settings.CATALOG_NAME}.{settings.SCHEMA_NAME}.{settings.TABLE_CHUNKS} WHERE pdf_id = '{pdf_name}'",

            # Delete page screenshots metadata
            f"DELETE FROM {settings.CATALOG_NAME}.{settings.SCHEMA_NAME}.{settings.TABLE_SCREENSHOTS} WHERE pdf_id = '{pdf_name}'",

            # Delete operator questions
            f"DELETE FROM {settings.CATALOG_NAME}.{settings.SCHEMA_NAME}.operator_questions WHERE pdf_id = '{pdf_name}'",

            # Delete document summaries
            f"DELETE FROM {settings.CATALOG_NAME}.{settings.SCHEMA_NAME}.document_summaries WHERE pdf_id = '{pdf_name}'",

            # Delete registry entry
            f"DELETE FROM {settings.CATALOG_NAME}.{settings.SCHEMA_NAME}.{settings.TABLE_REGISTRY} WHERE pdf_id = '{pdf_name}'"
        ]

        # Only attempt SQL cleanup if warehouse is configured
        if settings.SQL_WAREHOUSE_ID:
            for query in cleanup_queries:
                try:
                    w.statement_execution.execute_statement(
                        warehouse_id=settings.SQL_WAREHOUSE_ID,
                        statement=query,
                        wait_timeout="50s"
                    )
                except Exception as e:
                    print(f"Warning: Error during cleanup - {e}")
        else:
            print("Warning: SQL_WAREHOUSE_ID not set; skipping table cleanup")

        # Delete old PDF file from volume
        try:
            old_pdf_path = f"/Volumes/{settings.CATALOG_NAME}/{settings.SCHEMA_NAME}/{settings.VOLUME_RAW_PDFS}/{pdf_name}"
            w.files.delete(old_pdf_path)
            print(f"Deleted volume file: {pdf_name}")
        except Exception as e:
            print(f"Warning: Could not delete old PDF file - {e}")

        # Delete screenshot folder - using pdf_name as folder name now
        try:
            screenshot_dir = f"/Volumes/{settings.CATALOG_NAME}/{settings.SCHEMA_NAME}/{settings.VOLUME_SCREENSHOTS}/{pdf_name}/"
            w.files.delete(screenshot_dir)
            print(f"Deleted screenshot directory: {pdf_name}/")
        except Exception as e:
            print(f"Warning: Could not delete screenshot directory - {e}")


# Singleton instance
databricks_client = DatabricksClient()
