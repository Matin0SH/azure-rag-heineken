# NextLevel RAG API

REST API for PDF ingestion and processing using Databricks.

## Features

- **PDF Upload**: Upload PDF files for processing
- **Job Triggering**: Automatically trigger Databricks ingestion jobs
- **Status Tracking**: Monitor PDF and job processing status
- **API Key Authentication**: Secure endpoints with API key
- **OpenAPI Documentation**: Auto-generated API docs

## Project Structure

```
api/
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py         # Application settings
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── ingest.py           # PDF ingestion endpoints
│   │   └── status.py           # Status check endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── databricks_client.py  # Databricks API client
│   │   └── pdf_service.py      # Business logic
│   └── utils/
│       ├── __init__.py
│       └── auth.py             # Authentication utilities
├── tests/                      # Test files
├── .env.example                # Environment variables template
├── .gitignore
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose setup
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Setup

### 1. Prerequisites

- Python 3.11+
- Databricks workspace with:
  - Unity Catalog configured
  - Vector Search endpoint created
  - Ingestion job deployed
  - SQL Warehouse (optional)

### 2. Installation

```bash
# Clone the repository
cd api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# API Configuration
API_KEY=your-secure-api-key-here

# Databricks Configuration
DATABRICKS_HOST=https://your-workspace.azuredatabricks.net
DATABRICKS_TOKEN=your-token-here

# Job Configuration
INGEST_JOB_ID=your-job-id-here
```

### 4. Run the API

#### Local Development

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Using Docker

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d
```

### 5. Access the API

- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

## API Endpoints

### POST /api/v1/ingest-pdf

Upload and process a PDF file.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/ingest-pdf" \
  -H "X-API-Key: your-api-key" \
  -F "file=@/path/to/document.pdf"
```

**Response:**
```json
{
  "pdf_id": "123e4567-e89b-12d3-a456-426614174000",
  "pdf_name": "document.pdf",
  "job_run_id": 123456,
  "status": "processing",
  "message": "PDF 'document.pdf' uploaded and processing started"
}
```

### GET /api/v1/pdf-status/{pdf_id}

Get PDF processing status.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/pdf-status/{pdf_id}" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "pdf_id": "123e4567-e89b-12d3-a456-426614174000",
  "pdf_name": "document.pdf",
  "file_path": "/Volumes/catalog/schema/raw_pdfs/document.pdf",
  "upload_date": "2025-11-30T10:00:00Z",
  "processing_status": "completed",
  "processed_date": "2025-11-30T10:05:00Z",
  "error_message": null
}
```

### GET /api/v1/job-status/{run_id}

Get Databricks job run status.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/job-status/{run_id}" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "job_run_id": 123456,
  "state": "Running",
  "life_cycle_state": "RUNNING",
  "result_state": null,
  "start_time": 1701345600000,
  "end_time": null,
  "run_page_url": "https://..."
}
```

## Authentication

All endpoints require API key authentication via the `X-API-Key` header.

```bash
-H "X-API-Key: your-api-key-here"
```

## Error Handling

The API returns standard HTTP status codes:

- `200`: Success
- `400`: Bad Request (invalid file, validation error)
- `401`: Unauthorized (invalid/missing API key)
- `404`: Not Found (PDF/job not found)
- `413`: Payload Too Large (file size exceeds limit)
- `500`: Internal Server Error

**Error Response Format:**
```json
{
  "error": "error_type",
  "message": "Detailed error message",
  "details": {}
}
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black app/

# Lint
flake8 app/

# Type checking
mypy app/
```

## Deployment

### Azure Container Apps (Recommended)

1. Build and push Docker image:
```bash
docker build -t yourregistry.azurecr.io/nextlevel-api:latest .
docker push yourregistry.azurecr.io/nextlevel-api:latest
```

2. Deploy to Azure Container Apps:
```bash
az containerapp create \
  --name nextlevel-api \
  --resource-group your-rg \
  --image yourregistry.azurecr.io/nextlevel-api:latest \
  --environment your-env \
  --secrets api-key=your-key databricks-token=your-token \
  --env-vars "API_KEY=secretref:api-key" "DATABRICKS_TOKEN=secretref:databricks-token"
```

### Azure Functions (Alternative)

See Azure Functions deployment guide in `/docs/azure-functions.md`

## Configuration Options

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `API_KEY` | API authentication key | Yes | - |
| `DATABRICKS_HOST` | Databricks workspace URL | Yes | - |
| `DATABRICKS_TOKEN` | Databricks access token | Yes | - |
| `INGEST_JOB_ID` | Databricks job ID | Yes | - |
| `CATALOG_NAME` | Unity Catalog name | No | `heineken_test_workspace` |
| `SCHEMA_NAME` | Schema name | No | `nextlevel-rag` |
| `MAX_FILE_SIZE_MB` | Max upload size (MB) | No | `100` |

## Security Best Practices

1. **Never commit `.env` file** - Use environment variables or Azure Key Vault
2. **Rotate API keys regularly**
3. **Use HTTPS in production**
4. **Enable CORS only for trusted origins**
5. **Store Databricks tokens in Azure Key Vault**
6. **Implement rate limiting** (use Azure API Management)

## Troubleshooting

### Issue: "Invalid API key"
- Check `X-API-Key` header is set correctly
- Verify `API_KEY` in `.env` matches request header

### Issue: "Failed to trigger Databricks job"
- Verify `DATABRICKS_TOKEN` has correct permissions
- Check `INGEST_JOB_ID` is correct
- Ensure Databricks workspace is accessible

### Issue: "File too large"
- Check file size is under `MAX_FILE_SIZE_MB` limit
- Increase limit in `.env` if needed

## License

MIT

## Support

For issues and questions, please open an issue on GitHub.
