"""
Chat Router - RAG Q&A Endpoint
"""
from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.chat_service import chat_service
from app.utils.auth import validate_api_key

router = APIRouter()


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    },
    summary="RAG Chat Q&A",
    description="Ask questions about PDFs using Retrieval-Augmented Generation"
)
async def chat(
    request: ChatRequest,
    _: bool = Depends(validate_api_key)
):
    """
    RAG Chat Pipeline:

    1. **Vector Search**: Retrieve top K relevant chunks from vector index
    2. **Group by Page**: Combine chunks into full page contexts
    3. **Rerank**: LLM scores each page for relevance (0-10)
    4. **Answer**: Generate answer with Chain-of-Thought using top pages

    Args:
        request: ChatRequest with query, optional pdf_id filter, and top_k

    Returns:
        ChatResponse with answer, reasoning, citations, and metadata
    """
    try:
        result = chat_service.chat(
            query=request.query,
            pdf_id=request.pdf_id,
            top_k=request.top_k
        )
        return ChatResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {str(e)}"
        )
