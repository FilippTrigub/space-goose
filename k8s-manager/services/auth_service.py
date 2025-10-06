from typing import Optional
from fastapi import HTTPException, Header

from .mongodb_service import get_user_by_api_key



# # Dependency to get user from API key in headers
async def get_current_user(x_api_key: Optional[str] = Header(None)):
    """
    Extract API key from X-API-Key header and retrieve user from MongoDB.

    Args:
        x_api_key: Blackbox API key from request header

    Returns:
        User ID string

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is required")

    user = get_user_by_api_key(x_api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user["user_id"]
