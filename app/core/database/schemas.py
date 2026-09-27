import uuid
from datetime import datetime
from typing import Annotated
from pydantic import BaseModel, EmailStr, Field, ConfigDict, BeforeValidator  
from app.core.database.models import UserRole

def coerce_uuid(v: object) -> uuid.UUID | object:
    """Safely converts incoming string parameters into native UUID objects for SQLite compatibility."""
    if isinstance(v, str):
        try:
            return uuid.UUID(v)
        except ValueError:
            return v
    return v

SafeUUID = Annotated[uuid.UUID, BeforeValidator(coerce_uuid)]

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)

class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    organization_id: SafeUUID
    username: str = Field(..., min_length=3, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.MEMBER

class UserResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole
    
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
