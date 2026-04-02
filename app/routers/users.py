from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rbac import require_admin
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["User Management"])


@router.post(
    "/",
    response_model=UserResponse,
    status_code=201,
    summary="Create a new user [Admin only]",
    dependencies=[Depends(require_admin)],
)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(db, payload)


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="List all users [Admin only]",
    dependencies=[Depends(require_admin)],
)
def list_users(db: Session = Depends(get_db)):
    return user_service.list_users(db)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user by ID [Admin only]",
    dependencies=[Depends(require_admin)],
)
def get_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.get_user_by_id(db, user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update a user's role or status [Admin only]",
    dependencies=[Depends(require_admin)],
)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    return user_service.update_user(db, user_id, payload)


@router.delete(
    "/{user_id}",
    status_code=204,
    summary="Delete a user [Admin only]",
    dependencies=[Depends(require_admin)],
)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user_service.delete_user(db, user_id)
