import re
from fastapi import HTTPException, status
from typing import Optional

# List of dangerous patterns for basic prompt injection protection
DANGEROUS_PATTERNS = [
    r"ignore previous instructions",
    r"you are now",
    r"forget everything",
    r"system override"
]

def validate_input_query(query: str) -> str:
    """Validates text input for basic length and injection protection."""
    if not query or len(query) > 2000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query length must be between 1 and 2000 characters"
        )
        
    query_lower = query.lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, query_lower):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malicious input detected. Request rejected."
            )
            
    return query

def validate_image(mime_type: str, file_size: int):
    """Validates the uploaded image."""
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if mime_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type. Allowed types: {', '.join(allowed_types)}"
        )
        
    # Max size 10MB
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image size exceeds 10MB limit."
        )
    return True
