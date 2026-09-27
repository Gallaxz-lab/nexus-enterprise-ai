import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session


from app.core.database.connection import get_db
from app.core.dependencies.auth_deps import get_current_user
from app.core.database.models import User

from app.modules.audit.invoices.models import InvoiceModel
from app.modules.audit.purchase_orders.models import PurchaseOrderModel
from app.modules.audit.audits.models import AuditWorkflowModel
from app.modules.audit.audits.schemas import AuditWorkflowResponseSchema, HumanReviewSubmissionSchema
from app.modules.audit.audits.graph import audit_workflow_graph

router = APIRouter(prefix="/audit", tags=["Autonomous Audit Engine"])

@router.post("/compare/{invoice_id}/{po_id}", response_model=AuditWorkflowResponseSchema)
def compare_documents_workflow(
    invoice_id: uuid.UUID,
    po_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org_id = current_user.organization_id
    
    invoice = db.query(InvoiceModel).filter(InvoiceModel.invoice_id == invoice_id, InvoiceModel.organization_id == org_id).first()
    po = db.query(PurchaseOrderModel).filter(PurchaseOrderModel.po_id == po_id, PurchaseOrderModel.organization_id == org_id).first()
    
    if not invoice or not po:
        raise HTTPException(status_code=404, detail="Target structures not accessible within active tenant namespace.")

    # 1. Initialize parameters inside the Graph State Space
    initial_state = {
        "audit_id": uuid.uuid4(),
        "organization_id": org_id,
        "invoice": {"vendor": invoice.vendor, "items": invoice.items, "tax": invoice.tax, "total": invoice.total},
        "purchase_order": {"vendor": po.vendor, "items": po.items, "total": po.total},
        "discrepancies": [],
        "validation_errors": [],
        "confidence": 1.0,
        "retry_count": 0,
        "workflow_status": "START"
    }

    # 2. Run the LangGraph execution loop
    final_output = audit_workflow_graph.invoke(initial_state)
    
    # 3. Persist the final state back to the audit logs
    completed_time = datetime.utcnow() if final_output["workflow_status"] == "FINALIZED" else None
    
    db_workflow = AuditWorkflowModel(
        audit_id=initial_state["audit_id"],
        organization_id=org_id,
        invoice_id=invoice_id,
        po_id=po_id,
        workflow_status=final_output["workflow_status"],
        detected_discrepancies=final_output["discrepancies"],
        validation_errors=final_output["validation_errors"],
        ai_recheck_result=final_output["ai_recheck_result"],
        confidence=final_output["confidence"],
        retry_count=final_output["retry_count"],
        model_name="gpt-4o-mini",  # Tracks active generation parameters
        input_tokens=140,         # Mock tracking analytics details
        output_tokens=45,
        estimated_cost=0.002,
        completed_at=completed_time
    )
    
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    return db_workflow

@router.get("/{audit_id}/review", response_model=AuditWorkflowResponseSchema)
def get_workflow_for_review(
    audit_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record = db.query(AuditWorkflowModel).filter(
        AuditWorkflowModel.audit_id == audit_id, 
        AuditWorkflowModel.organization_id == current_user.organization_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Target processing record missing.")
    return record

@router.post("/{audit_id}/review", response_model=AuditWorkflowResponseSchema)
def submit_human_review(
    audit_id: uuid.UUID,
    payload: HumanReviewSubmissionSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    record = db.query(AuditWorkflowModel).filter(
        AuditWorkflowModel.audit_id == audit_id, 
        AuditWorkflowModel.organization_id == current_user.organization_id
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="Target processing record missing.")
        
    if record.workflow_status != "HUMAN_REVIEW":
        raise HTTPException(status_code=400, detail="This tracking flow does not require operational review.")

    record.human_decision = {
        "decision": payload.decision,
        "comment": payload.comment,
        "reviewed_by": str(current_user.user_id)
    }
    record.workflow_status = "FINALIZED" if payload.decision == "approved" else "REJECTED"
    record.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(record)
    return record
