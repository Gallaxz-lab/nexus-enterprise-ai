from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Dict
from uuid import UUID
from datetime import datetime

# ======================================================================================
# CORE DISCREPANCY ARRAYS (Shared across deterministic engine and Graph States)
# ======================================================================================

class DiscrepancyDetailSchema(BaseModel):
    field: str  # "quantity", "unit_price", "product_mismatch", "total_mismatch", "missing_item"
    product: Optional[str] = None
    invoice_value: Any
    po_value: Any
    difference: Optional[float] = None

class AuditResponseSchema(BaseModel):
    audit_id: UUID
    organization_id: UUID
    invoice_id: UUID
    po_id: UUID
    status: str
    discrepancies: List[DiscrepancyDetailSchema]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True) 


# ======================================================================================
# WORKFLOW AGENT & INTERACTION EXTRACTIONS
# ======================================================================================

class AIRecheckSchema(BaseModel):
    valid_discrepancy: bool = Field(..., description="Flags if the discrepancy appears to be a true transactional error")
    reason: str = Field(..., description="Detailed textual rationale behind the evaluation signature")
    confidence: float = Field(..., description="Statistical or algorithmic certainty indicator score from 0.0 to 1.0")

class HumanReviewSubmissionSchema(BaseModel):
    decision: str = Field(..., description="Must evaluate directly to 'approved' or 'rejected'")
    comment: str = Field(..., description="Contextual narrative tracking why this decision was taken")

class AuditWorkflowResponseSchema(BaseModel):
    audit_id: UUID
    organization_id: UUID
    invoice_id: UUID
    po_id: UUID
    workflow_status: str
    detected_discrepancies: List[DiscrepancyDetailSchema]
    validation_errors: List[str]
    ai_recheck_result: Optional[Dict[str, Any]] = None
    confidence: float
    retry_count: int
    human_decision: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True) 
