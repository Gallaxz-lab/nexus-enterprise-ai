import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, UUID, JSON
from datetime import datetime, timezone
from app.core.database.connection import Base

class JobProfile(Base):
    __tablename__ = "job_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String(255), nullable=False)
    seniority = Column(String(100), nullable=True)
    required_experience = Column(String(255), nullable=True)
    education = Column(String(255), nullable=True)
    
    # Structural arrays stored as JSON documents
    responsibilities = Column(JSON, nullable=False, default=list)
    required_skills = Column(JSON, nullable=False, default=list)
    preferred_skills = Column(JSON, nullable=False, default=list)
    technologies = Column(JSON, nullable=False, default=list)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    embedding = Column(JSON, nullable=True)