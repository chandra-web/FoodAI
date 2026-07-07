"""
JWT Authentication module for FoodAI.

Provides:
  - Password hashing / verification (bcrypt via passlib)
  - JWT creation / verification (python-jose)
  - FastAPI dependency: get_current_user()
  - Legacy X-API-Key verification: verify_api_key()
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_32_CHARS_MIN")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 h

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(plain_password: str) -> str:
    """Return the bcrypt hash of *plain_password*."""
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches the stored *hashed_password*."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(
    subject: str,
    *,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    """
    Create a signed JWT.

    Args:
        subject: Typically the user's UUID string.
        expires_delta: Custom TTL; defaults to ACCESS_TOKEN_EXPIRE_MINUTES.
        extra_claims: Additional payload fields merged into the token.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict = {"sub": subject, "exp": expire, "iat": datetime.utcnow()}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> str:
    """
    Decode and verify a JWT.

    Returns:
        The ``sub`` claim (user_id) if the token is valid.

    Raises:
        HTTPException 401 if the token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise credentials_exception


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    FastAPI dependency that extracts and validates the Bearer token.

    Returns the ``user_id`` string from the JWT ``sub`` claim.

    Usage::

        @app.get("/protected")
        async def protected(user_id: str = Depends(get_current_user)):
            ...
    """
    return verify_token(token)


# ---------------------------------------------------------------------------
# Legacy X-API-Key support (kept for backward-compatible endpoints)
# ---------------------------------------------------------------------------

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
_VALID_API_KEYS: list[str] = [
    k for k in [os.getenv("FOODAI_API_KEY"), os.getenv("GOOGLE_API_KEY")] if k
]


async def verify_api_key(api_key: Optional[str] = Security(_API_KEY_HEADER)) -> str:
    """
    FastAPI security dependency that validates an X-API-Key header.

    Used by legacy endpoints that predate the JWT auth system.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header is missing",
        )
    if api_key not in _VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key
