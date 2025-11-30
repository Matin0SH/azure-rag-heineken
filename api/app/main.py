"""
FastAPI Application - PDF Ingestion REST API
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.routers import ingest, status
from app.config.settings import settings

app = FastAPI(
    title="NextLevel RAG API",
    description="REST API for PDF ingestion and processing",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include routers
app.include_router(ingest.router, prefix="/api/v1", tags=["Ingestion"])
app.include_router(status.router, prefix="/api/v1", tags=["Status"])

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "nextlevel-rag-api"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "NextLevel RAG API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc)
        }
    )
