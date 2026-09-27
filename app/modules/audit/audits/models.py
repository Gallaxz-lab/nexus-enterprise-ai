import uuid
from datetime import datetime
from sqlalchemy import Column, String, ForeignKey, DateTime, JSON, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.models import Base

class AuditWorkflowModel(Base):
    __tablename__ = "audit_workflows"

    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("audit_invoices.invoice_id"), nullable=False)
    po_id = Column(UUID(as_uuid=True), ForeignKey("audit_purchase_orders.po_id"), nullable=False)
    
    # Workflow Status tracking matrix
    workflow_status = Column(String, default="START") # START, VALIDATED, COMPARED, RECHECKED, FINALIZED, HUMAN_REVIEW
    detected_discrepancies = Column(JSON, default=list)
    validation_errors = Column(JSON, default=list)
    
    # AI Re-check verification logs
    ai_recheck_result = Column(JSON, nullable=True) 
    confidence = Column(Float, default=1.0)
    retry_count = Column(Integer, default=0)
    
    # Human Review interaction outcomes
    human_decision = Column(JSON, nullable=True)
    
    # Token Metadata and Financial Observability Tracking
    model_name = Column(String, nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
