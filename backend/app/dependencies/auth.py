import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.jwt import decode_access_token
from app.db.session import get_db
from app.models.user import User
from jwt import ExpiredSignatureError, InvalidTokenError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except ExpiredSignatureError:
        raise expired_exception
    except InvalidTokenError:
        raise credentials_exception

    # Validate UUID format
    try:
        uid = uuid.UUID(user_id)  # type: ignore[arg-type]
    except (ValueError, AttributeError):
        raise credentials_exception

    user = db.get(User, uid)
    if user is None:
        raise credentials_exception
    return user
