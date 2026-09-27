import uuid
from enum import Enum
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum, UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database.connection import Base

class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    username = Column(String(150), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.MEMBER)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    organization = relationship("Organization", back_populates="users")
