from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.database import models, schemas
from app.core.auth import security

class AuthService:
    @staticmethod
    def authenticate_user(payload: schemas.LoginRequest, db: Session) -> dict:
        user = db.query(models.User).filter(models.User.username == payload.username).first()
        if not user or not security.verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid username or password."
            )
        
        token_claims = {"sub": str(user.id), "org_id": str(user.organization_id), "role": user.role.value}
        token = security.create_access_token(data=token_claims)
        return {"access_token": token, "token_type": "bearer"}

    @staticmethod
    def register_new_operator(user_in: schemas.UserCreate, db: Session) -> models.User:
        org = db.query(models.Organization).filter(models.Organization.id == user_in.organization_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Target tenant organization not found.")
            
        collision = db.query(models.User).filter(
            (models.User.username == user_in.username) | (models.User.email == user_in.email)
        ).first()
        if collision:
            raise HTTPException(status_code=400, detail="Username or email identifier already registered.")

        new_user = models.User(
            organization_id=user_in.organization_id,
            username=user_in.username,
            email=user_in.email,
            hashed_password=security.hash_password(user_in.password),
            role=user_in.role
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
