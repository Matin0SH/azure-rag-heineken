"""
Databricks API Client Service
"""
import requests
from typing import Dict, Any, Optional
import uuid

from app.config.settings import settings

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


# Singleton instance
databricks_client = DatabricksClient()
