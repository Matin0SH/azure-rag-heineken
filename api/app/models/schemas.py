"""
Pydantic Models for API Request/Response Validation
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class IngestResponse(BaseModel):
    pdf_id: str = Field(..., description="Unique PDF identifier")
    pdf_name: str = Field(..., description="Original PDF filename")
    job_run_id: int = Field(..., description="Databricks job run ID")
    status: ProcessingStatus = Field(..., description="Processing status")
    message: str = Field(..., description="Response message")

class StatusResponse(BaseModel):
    pdf_id: str
    pdf_name: str
    file_path: str
    upload_date: datetime
    processing_status: ProcessingStatus
    processed_date: Optional[datetime] = None
    error_message: Optional[str] = None

class JobStatusResponse(BaseModel):
    job_run_id: int
    state: str
    life_cycle_state: str
    result_state: Optional[str] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    run_page_url: str

class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
