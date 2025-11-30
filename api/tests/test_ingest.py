"""
Tests for PDF ingestion endpoints
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Mock API key for testing
VALID_API_KEY = "test-api-key"
INVALID_API_KEY = "wrong-key"

def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_ingest_pdf_no_auth():
    """Test ingestion without API key"""
    response = client.post("/api/v1/ingest-pdf")
    assert response.status_code == 401

def test_ingest_pdf_invalid_auth():
    """Test ingestion with invalid API key"""
    response = client.post(
        "/api/v1/ingest-pdf",
        headers={"X-API-Key": INVALID_API_KEY}
    )
    assert response.status_code == 401

# Add more tests as needed
