from typing import Dict, Any, List, Literal, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END

from app.core.ai_factory.llm import AIFactory
from app.modules.audit.invoices.models import InvoiceModel
from app.modules.audit.purchase_orders.models import PurchaseOrderModel
from app.modules.audit.audits.services import DiscrepancyEngine
from app.modules.audit.audits.schemas import AIRecheckSchema

# 1. State Space Structure Definition
class AuditState(BaseModel):
    audit_id: UUID
    organization_id: UUID
    invoice: Dict[str, Any]
    purchase_order: Dict[str, Any]
    discrepancies: List[Dict[str, Any]] = []
    validation_errors: List[str] = []
    confidence: float = 1.0
    retry_count: int = 0
    ai_recheck_result: Optional[Dict[str, Any]] = None
    workflow_status: str = "START"

# ======================================================================================
# NODE EXECUTION UTILITIES
# ======================================================================================

def extract_load_node(state: AuditState) -> Dict[str, Any]:
    """Ensures data sets are available for matching downstream."""
    return {"workflow_status": "LOADED"}

def validate_node(state: AuditState) -> Dict[str, Any]:
    """Enforces foundational business logic invariants prior to comparison."""
    errors = []
    inv = state.invoice
    po = state.purchase_order
    
    if inv.get("vendor") != po.get("vendor"):
        errors.append(f"Vendor mismatch layout: '{inv.get('vendor')}' vs '{po.get('vendor')}'")
    
    return {
        "validation_errors": errors,
        "workflow_status": "VALIDATED"
    }

def compare_node(state: AuditState) -> Dict[str, Any]:
    """Enforces absolute pure Python mathematical reconciliation patterns."""
    # Instantiates mock models to safely call your deterministic Phase 3 engine
    mock_inv = InvoiceModel(
        items=state.invoice.get("items", []),
        tax=state.invoice.get("tax", 0.0),
        total=state.invoice.get("total", 0.0)
    )
    mock_po = PurchaseOrderModel(
        items=state.purchase_order.get("items", []),
        total=state.purchase_order.get("total", 0.0)
    )
    
    issues = DiscrepancyEngine.run_reconciliation(mock_inv, mock_po)
    return {
        "discrepancies": issues,
        "workflow_status": "COMPARED"
    }

def recheck_node(state: AuditState) -> Dict[str, Any]:
    """Delegates cognitive assessment to the structured AIFactory."""
    current_retry = state.retry_count
    
    prompt = f"""
    Analyze the following transactional matching payload structures for internal inconsistencies:
    Invoice Structure: {state.invoice}
    Purchase Order Structure: {state.purchase_order}
    Deterministic Anomalies Detected by Python Matrix: {state.discrepancies}
    
    Evaluate if this discrepancy appears valid or could stem from variations like synonyms, abbreviations, or units.
    """
    
    try:
        # Calls your production AIFactory template safely
        ai_evaluation: AIRecheckSchema = AIFactory.generate_structured_json(
            prompt=prompt,
            response_schema=AIRecheckSchema
        )
        
        return {
            "ai_recheck_result": ai_evaluation.model_dump(),
            "confidence": ai_evaluation.confidence,
            "workflow_status": "RECHECKED",
            "retry_count": current_retry + 1
        }
    except Exception as e:
        # Explicitly records system provider failures to route workflows cleanly to Human Review
        return {
            "ai_recheck_result": {"valid_discrepancy": True, "reason": f"AI Factory failure: {str(e)}", "confidence": 0.0},
            "confidence": 0.0,
            "workflow_status": "RECHECK_FAILED",
            "retry_count": current_retry + 1
        }

def finalize_node(state: AuditState) -> Dict[str, Any]:
    """Closes matching sequences that resolve cleanly without edge anomalies."""
    return {"workflow_status": "FINALIZED"}

def human_review_node(state: AuditState) -> Dict[str, Any]:
    """Transitions state processing cleanly to human reviewers."""
    return {"workflow_status": "HUMAN_REVIEW"}

# ======================================================================================
# CONDITIONAL ROUTING ROUTINES
# ======================================================================================

def route_after_comparison(state: AuditState) -> Literal["approve", "recheck"]:
    if len(state.discrepancies) == 0 and len(state.validation_errors) == 0:
        return "approve"
    return "recheck"

def route_after_recheck(state: AuditState) -> Literal["finalize", "human_review", "retry"]:
    if state.workflow_status == "RECHECK_FAILED":
        if state.retry_count < 2:
            return "retry"
        return "human_review"
        
    if state.confidence >= 0.85:
        return "finalize"
    return "human_review"

# ======================================================================================
# GRAPH PIPELINE ASSEMBLER
# ======================================================================================

builder = StateGraph(AuditState)

# Mount operational components
builder.add_node("extract_load", extract_load_node)
builder.add_node("validate", validate_node)
builder.add_node("compare", compare_node)
builder.add_node("recheck", recheck_node)
builder.add_node("finalize", finalize_node)
builder.add_node("human_review", human_review_node)

# Map edge constraints
builder.add_edge(START, "extract_load")
builder.add_edge("extract_load", "validate")
builder.add_edge("validate", "compare")

builder.add_conditional_edges(
    "compare",
    route_after_comparison,
    {
        "approve": "finalize",
        "recheck": "recheck"
    }
)

builder.add_conditional_edges(
    "recheck",
    route_after_recheck,
    {
        "finalize": "finalize",
        "human_review": "human_review",
        "retry": "recheck"
    }
)

builder.add_edge("finalize", END)
builder.add_edge("human_review", END)

# Compile into a production execution engine workflow
audit_workflow_graph = builder.compile()
