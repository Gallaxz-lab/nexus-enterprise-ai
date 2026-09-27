import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, UUID, JSON, Integer, Float
from datetime import datetime, timezone
from app.core.database.connection import Base

class EvaluationAuditRecord(Base):
    __tablename__ = "evaluation_audit_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("job_profiles.id", ondelete="CASCADE"), nullable=False)
    
    model_provider = Column(String(100), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    
    # Stores the raw validation payload safely as JSON text snapshots
    evaluation_result = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
