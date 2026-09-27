from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database.connection import get_db
from app.core.database import models, schemas
from app.core.services.auth_service import AuthService
from app.core.dependencies import auth_deps

router = APIRouter(tags=["Identity Layer"])

@router.post("/auth/users", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    return AuthService.register_new_operator(user_in, db)

@router.post("/auth/login", response_model=schemas.TokenResponse)
def login_authenticate(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    return AuthService.authenticate_user(payload, db)

@router.get("/auth/me", response_model=schemas.UserResponse)
def get_current_user_profile(current_user: models.User = Depends(auth_deps.get_current_user)):
    return current_user
