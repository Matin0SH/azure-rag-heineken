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

class SummaryType(str, Enum):
    TECHNICAL = "technical"
    OPERATOR = "operator"

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

class SummarizationRequest(BaseModel):
    pdf_id: str = Field(..., description="PDF identifier (pdf_name)")
    summary_type: SummaryType = Field(..., description="Type of summary to generate")

class SummarizationResponse(BaseModel):
    pdf_id: str = Field(..., description="PDF identifier")
    pdf_name: str = Field(..., description="PDF filename")
    summary_type: SummaryType = Field(..., description="Summary type requested")
    job_run_id: int = Field(..., description="Databricks job run ID")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Response message")

class QuestionGenerationRequest(BaseModel):
    pdf_id: str = Field(..., description="PDF identifier (pdf_name)")

class QuestionGenerationResponse(BaseModel):
    pdf_id: str = Field(..., description="PDF identifier")
    pdf_name: str = Field(..., description="PDF filename")
    job_run_id: int = Field(..., description="Databricks job run ID")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Response message")

class PDFListItem(BaseModel):
    pdf_id: str
    pdf_name: str
    processing_status: ProcessingStatus
    upload_date: datetime
    processed_date: Optional[datetime] = None

class PDFListResponse(BaseModel):
    pdfs: list[PDFListItem]
    total: int

class SummaryListItem(BaseModel):
    summary_id: str
    pdf_id: str
    pdf_name: str
    summary_type: SummaryType
    created_at: datetime

class SummaryListResponse(BaseModel):
    summaries: list[SummaryListItem]
    total: int

class QuestionListItem(BaseModel):
    questions_id: str
    pdf_id: str
    pdf_name: str
    created_at: datetime
    num_questions: Optional[int] = None

class QuestionListResponse(BaseModel):
    questions: list[QuestionListItem]
    total: int

# ===========================
# RAG CHAT SCHEMAS
# ===========================

class ChatRequest(BaseModel):
    query: str = Field(..., description="User's question", min_length=1)
    pdf_id: Optional[str] = Field(None, description="Filter by specific PDF (optional)")
    top_k: int = Field(20, description="Number of chunks to retrieve", ge=1, le=100)

class Citation(BaseModel):
    doc_num: int = Field(..., description="Document number in context (1-indexed)")
    pdf_id: str = Field(..., description="PDF identifier")
    page_number: int = Field(..., description="Page number in PDF")

class PageRank(BaseModel):
    pdf_id: str
    page_number: int
    rerank_score: float
    text_preview: str = Field(..., description="First 200 chars of page text")

class ChatResponse(BaseModel):
    query: str = Field(..., description="Original user query")
    answer: str = Field(..., description="Generated answer")
    reasoning: str = Field(..., description="Chain-of-thought reasoning")
    citations: list[Citation] = Field(default_factory=list, description="Cited documents")
    cited_pages: list[tuple[str, int]] = Field(default_factory=list, description="(pdf_id, page_number) tuples")
    num_chunks_retrieved: int = Field(..., description="Number of chunks retrieved from vector search")
    num_pages_ranked: int = Field(..., description="Number of unique pages after grouping")
    top_reranked_pages: list[PageRank] = Field(default_factory=list, description="Top 5 pages with rerank scores")
