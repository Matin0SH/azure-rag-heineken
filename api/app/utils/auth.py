"""
Authentication and Authorization utilities
"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config.settings import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def validate_api_key(api_key: str = Security(api_key_header)):
    """
    Validate API key from request header

    Args:
        api_key: API key from X-API-Key header

    Returns:
        True if valid

    Raises:
        HTTPException: If API key is invalid
    """
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return True
