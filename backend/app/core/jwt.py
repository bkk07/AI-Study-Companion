from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import get_settings


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create HS256 JWT with `sub` = subject (user id string)."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None else timedelta(minutes=settings.jwt_expire_minutes)
    )
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    encoded = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return encoded


def decode_access_token(token: str) -> dict:
    """Decode and verify token, raising ExpiredSignatureError/InvalidTokenError on failure."""
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return payload


def get_token_subject(token: str) -> Optional[str]:
    try:
        payload = decode_access_token(token)
        return payload.get("sub")
    except (ExpiredSignatureError, InvalidTokenError):
        return None
