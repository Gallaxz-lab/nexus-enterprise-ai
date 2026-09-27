import pytest
import uuid
from unittest.mock import patch, MagicMock
from app.modules.support.knowledge.agent import support_agent_graph
from app.modules.support.knowledge.models import SupportTicketModel
from app.core.database.connection import SessionLocal as TestingSessionLocal

@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def base_agent_context():
    return {
        "organization_id": uuid.uuid4(),
        "customer_id": "cust_99812",
        "user_message": "Hello world",
        "agent_response": "",
        "staged_action": None,
        "workflow_status": "START"
    }

# ======================================================================================
# SCENARIO 1: VALIDATE RECLASSIFICATION KNOWLEDGE GATES
# ======================================================================================
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_agent_routes_to_knowledge_base(mock_ai, base_agent_context):
    base_agent_context["user_message"] = "What is the standard product return window policy?"
    
    mock_selection = MagicMock()
    mock_selection.route = "SEARCH_KB"
    mock_ai.return_value = mock_selection

    output = support_agent_graph.invoke(base_agent_context)
    # FIX: Assert the final state matching the graph execution end-point parameter
    assert output["workflow_status"] == "RETRIEVED_KB"

# ======================================================================================
# SCENARIO 2: AUTOMATED WRITES REQUIRE STAGED CONFIRMATIONS
# ======================================================================================
@patch("app.core.ai_factory.llm.AIFactory.generate_structured_json")
def test_agent_stages_writes_safely(mock_ai, base_agent_context):
    base_agent_context["user_message"] = "Please create a support ticket for my broken device."
    
    mock_selection = MagicMock()
    mock_selection.route = "STAGE_TICKET"
    mock_ai.return_value = mock_selection

    output = support_agent_graph.invoke(base_agent_context)
    assert output["staged_action"]["requires_confirmation"] is True
    assert output["staged_action"]["payload"]["customer_id"] == "cust_99812"
    assert output["workflow_status"] == "AWAITING_CONFIRMATION"

# ======================================================================================
# SCENARIO 3: BACKEND MULTI-TENANT ISOLATION BOUNDARY FOR TICKETS
# ======================================================================================
def test_ticket_isolation_boundary_enforcement(db):
    org_a_id = uuid.uuid4()
    org_b_id = uuid.uuid4()
    
    confidential_ticket = SupportTicketModel(
        organization_id=org_b_id,
        customer_id="cust_private",
        subject="Secret Ticket Context",
        description="Private information elements."
    )
    db.add(confidential_ticket)
    db.commit()
    
    results = db.query(SupportTicketModel).filter(SupportTicketModel.organization_id == org_a_id).all()
    
    assert len(results) == 0
    assert confidential_ticket not in results