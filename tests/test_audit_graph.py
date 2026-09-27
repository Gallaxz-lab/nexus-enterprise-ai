import pytest
import uuid
from unittest.mock import patch
from app.modules.audit.audits.graph import audit_workflow_graph
from app.modules.audit.audits.schemas import AIRecheckSchema  # Import your structural schema

@pytest.fixture
def base_context():
    return {
        "audit_id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "invoice": {"vendor": "Acme Corp", "items": [], "tax": 0.0, "total": 0.0},
        "purchase_order": {"vendor": "Acme Corp", "items": [], "total": 0.0},
        "discrepancies": [],
        "validation_errors": [],
        "confidence": 1.0,
        "retry_count": 0,
        "workflow_status": "START"
    }

# ======================================================================================
# SCENARIO 1: PERFECT RECORD MATCHING MATCH FLOW
# ======================================================================================
def test_graph_scenario_1_perfect_match(base_context):
    base_context["invoice"]["items"] = [{"product": "Item A", "quantity": 5, "unit_price": 10.0, "total": 50.0}]
    base_context["invoice"]["total"] = 50.0
    base_context["purchase_order"]["items"] = [{"product": "Item A", "quantity": 5, "unit_price": 10.0, "total": 50.0}]
    base_context["purchase_order"]["total"] = 50.0

    output = audit_workflow_graph.invoke(base_context)
    assert output["workflow_status"] == "FINALIZED"
    assert len(output["discrepancies"]) == 0

# ======================================================================================
# SCENARIO 2: QUANTITY MISMATCH WITH HIGH CONFIDENCE
# ======================================================================================
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_graph_scenario_2_obvious_mismatch(mock_ai, base_context):
    base_context["invoice"]["items"] = [{"product": "Laptop", "quantity": 100, "unit_price": 500.0, "total": 50000.0}]
    base_context["invoice"]["total"] = 50000.0
    base_context["purchase_order"]["items"] = [{"product": "Laptop", "quantity": 80, "unit_price": 500.0, "total": 40000.0}]
    base_context["purchase_order"]["total"] = 40000.0

    # FIX: Instantiate an actual validated Pydantic model contract to ensure compliance
    mock_ai.return_value = AIRecheckSchema(
        valid_discrepancy=True,
        reason="True billing leakage confirmed.",
        confidence=0.95
    )

    output = audit_workflow_graph.invoke(base_context)
    assert output["workflow_status"] == "FINALIZED"
    assert output["confidence"] >= 0.85

# ======================================================================================
# SCENARIO 3: AMBIGUOUS MISMATCH ROUTING TO HUMAN REVIEW
# ======================================================================================
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_graph_scenario_3_ambiguous_mismatch(mock_ai, base_context):
    base_context["invoice"]["items"] = [{"product": "MacBook Pro M3", "quantity": 1, "unit_price": 2000.0, "total": 2000.0}]
    base_context["invoice"]["total"] = 2000.0
    base_context["purchase_order"]["items"] = [{"product": "Apple Laptop", "quantity": 1, "unit_price": 2000.0, "total": 2000.0}]
    base_context["purchase_order"]["total"] = 2000.0

    # FIX: Instantiate an actual validated Pydantic model contract to ensure compliance
    mock_ai.return_value = AIRecheckSchema(
        valid_discrepancy=True,
        reason="Descriptions differ wildly; unsure if units cross-align.",
        confidence=0.60
    )

    output = audit_workflow_graph.invoke(base_context)
    assert output["workflow_status"] == "HUMAN_REVIEW"

# ======================================================================================
# SCENARIO 4: TRANSIENT AI SYSTEM FAILURE AND RETRY GATES
# ======================================================================================
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_graph_scenario_4_ai_failure_retry_limit(mock_ai, base_context):
    base_context["invoice"]["items"] = [{"product": "Broken Link", "quantity": 1, "unit_price": 10.0, "total": 10.0}]
    
    # Simulate recurring server infrastructure issues
    mock_ai.side_effect = Exception("Connection timed out.")

    output = audit_workflow_graph.invoke(base_context)
    assert output["workflow_status"] == "HUMAN_REVIEW"
    assert output["retry_count"] >= 2
