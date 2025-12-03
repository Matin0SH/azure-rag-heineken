"""
FastAPI Application - PDF Ingestion REST API
Databricks Apps Compatible
"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.routers import ingest, status, summarization, question_generation
from app.config.settings import settings

# Get port from environment (Databricks Apps injects DATABRICKS_APP_PORT)
APP_PORT = int(os.getenv("DATABRICKS_APP_PORT", "8000"))

# Detect if running on Databricks Apps
IS_DATABRICKS_APPS = os.getenv("DATABRICKS_HOST") is not None

app = FastAPI(
    title="NextLevel RAG API",
    description="REST API for PDF ingestion, processing, summarization, and question generation",
    version="1.0.0",
    docs_url="/api/docs",        # OAuth2 protected on Databricks Apps
    redoc_url="/api/redoc",      # OAuth2 protected on Databricks Apps
    openapi_url="/api/openapi.json"  # OAuth2 protected on Databricks Apps
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
app.include_router(summarization.router, prefix="/api/v1", tags=["Summarization"])
app.include_router(question_generation.router, prefix="/api/v1", tags=["Question Generation"])

# Health check (public, no /api prefix)
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "nextlevel-rag-api",
        "environment": "databricks-apps" if IS_DATABRICKS_APPS else "local",
        "workspace": os.getenv("DATABRICKS_WORKSPACE_ID", "local")
    }

# Root endpoint (public)
@app.get("/")
async def root():
    return {
        "message": "NextLevel RAG API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "environment": "databricks-apps" if IS_DATABRICKS_APPS else "local"
    }

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Don't expose internal errors in production (Databricks Apps)
    if IS_DATABRICKS_APPS:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )
    # Show details in local development
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc)
        }
    )

# Application startup
if __name__ == "__main__":
    import uvicorn
    print(f"Starting FastAPI on port {APP_PORT}")
    print(f"Environment: {'Databricks Apps' if IS_DATABRICKS_APPS else 'Local'}")
    uvicorn.run(app, host="0.0.0.0", port=APP_PORT)
