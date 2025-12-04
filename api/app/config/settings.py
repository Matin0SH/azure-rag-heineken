"""
Application Settings and Configuration
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # API Configuration
    API_KEY: str = "your-api-key-here"
    ALLOWED_ORIGINS: List[str] = ["*"]

    # Databricks Configuration
    DATABRICKS_HOST: str
    DATABRICKS_TOKEN: str

    # Unity Catalog Configuration
    CATALOG_NAME: str = "databricks_rag_dev"
    SCHEMA_NAME: str = "nextlevel-rag"

    # Volume Configuration
    VOLUME_RAW_PDFS: str = "raw_pdfs"
    VOLUME_SCREENSHOTS: str = "screenshots"

    # Table Configuration
    TABLE_CHUNKS: str = "chunks_embedded"
    TABLE_REGISTRY: str = "pdf_registery"
    TABLE_SCREENSHOTS: str = "page_screenshots"

    # Vector Search Configuration
    VECTOR_SEARCH_ENDPOINT: str = "heineken-vdb"
    VECTOR_INDEX_NAME: str = "chunks_embedded_index"

    # LLM Configuration
    LLM_ENDPOINT: str = "databricks-llama-4-maverick"

    # Job Configuration
    INGEST_JOB_ID: int
    SUMMARIZATION_JOB_ID: int
    QUESTION_GENERATION_JOB_ID: int
    EMBEDDING_MODEL: str = "databricks-gte-large-en"

    # SQL Warehouse Configuration (optional)
    SQL_WAREHOUSE_ID: str = ""

    # File Upload Configuration
    MAX_FILE_SIZE_MB: int = 1000
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
