from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rbac import get_current_user
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import authenticate_user, generate_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Login and receive a JWT token")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    token = generate_token(user)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse, summary="Get the currently authenticated user")
def me(current_user: User = Depends(get_current_user)):
    return current_user
