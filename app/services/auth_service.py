from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models.user import User


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the user if credentials are valid, otherwise None."""
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def generate_token(user: User) -> str:
    return create_access_token(data={"sub": str(user.id), "role": user.role.value})
