from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from pwdlib import PasswordHash
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import uuid 
from app.config import settings
from app.core.database.connection import get_db
from app.core.database import models

# Setup password hashing engine using bcrypt
password_engine = PasswordHash.recommended()
security_bearer = HTTPBearer()

def hash_password(password: str) -> str:
    return password_engine.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_engine.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security_bearer),
    db: Session = Depends(get_db)
) -> models.User:
    """Decodes incoming tokens to verify active database records."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session invalid or expired. Access denied.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")  # This returns a plain text string
        if user_id_str is None:
            raise credentials_exception
            
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise credentials_exception

    except JWTError:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise credentials_exception
    return user


class RoleGuard:
    """Enforces minimum Role-Based Access Control requirements across targeted routes."""
    def __init__(self, required_roles: list[models.UserRole]):
        self.required_roles = required_roles

    def __call__(self, current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in self.required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security Clearance Denied: Administrative authority required."
            )
        return current_user