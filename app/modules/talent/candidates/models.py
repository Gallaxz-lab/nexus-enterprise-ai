import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, UUID, JSON, Integer
from datetime import datetime, timezone
from app.core.database.connection import Base   

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    summary = Column(String, nullable=True)
    
    # Structural fields stored as rich queryable JSON documents
    skills = Column(JSON, nullable=False, default=list)
    experience = Column(JSON, nullable=False, default=list)
    education = Column(JSON, nullable=False, default=list)
    languages = Column(JSON, nullable=False, default=list)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    embedding = Column(JSON, nullable=True)
    
    seniority = Column(String(100), nullable=True)    
    years_experience = Column(Integer, nullable=True, default=0)
    technologies = Column(JSON, nullable=False, default=list)
    
    evaluation_matrix = Column(JSON, nullable=True)