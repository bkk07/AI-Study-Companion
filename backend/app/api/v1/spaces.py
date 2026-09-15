from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.authorization import get_authorized_space
from app.db.session import get_db
from app.models.space import Space
from app.models.user import User
from app.schemas.space import SpaceCreate, SpaceRead
from app.services import space_service

router = APIRouter(prefix="/spaces", tags=["spaces"])


@router.post("", response_model=SpaceRead, status_code=status.HTTP_201_CREATED)
def create_space(
    payload: SpaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        space = space_service.create_space(db, current_user.id, payload.name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return space


@router.get("", response_model=list[SpaceRead])
def list_spaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    spaces = space_service.list_spaces(db, current_user.id)
    return spaces


@router.get("/{space_id}", response_model=SpaceRead)
def get_space(
    space: Space = Depends(get_authorized_space),
):
    return space
