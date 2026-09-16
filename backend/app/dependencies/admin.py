from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.models.user import User


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Separate privilege boundary over the same JWT identity.

    Anonymous callers fail upstream in `get_current_user` (401); authenticated
    non-admins are refused here (403) so existence of admin routes is
    acknowledged but never served to them.
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
