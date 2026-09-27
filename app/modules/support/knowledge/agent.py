from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy.orm import Session
from langgraph.graph import StateGraph, START, END

from app.core.ai_factory.llm import AIFactory
from app.modules.support.search.services import TenantIsolatedSearchEngine
from app.modules.support.knowledge.models import SupportTicketModel

# 1. Internal Agent State Definition Matrix
class AgentState(BaseModel):
    organization_id: UUID
    customer_id: str
    user_message: str
    agent_response: str = ""
    staged_action: Optional[Dict[str, Any]] = None
    workflow_status: str = "START"

# ======================================================================================
# CONTROLLED AGENT EXECUTOR NODES
# ======================================================================================

def core_routing_node(state: AgentState) -> Dict[str, Any]:
    """Uses the Agnostic LLM Factory to securely parse text and pick appropriate operational tasks."""
    prompt = f"""
    You are the Nexus Enterprise Support Agent. Analyze this user message: "{state.user_message}"
    
    Select the single most appropriate action from these three valid choices:
    1. "SEARCH_KB" - If the user is asking a general policy, company documentation, or knowledge question.
    2. "STAGE_TICKET" - If the user explicitly asks to log, open, or create a support ticket.
    3. "GENERAL_REPLY" - For basic greetings or general feedback that doesn't involve data writes.
    
    Respond with a single word matching the selected token signature option.
    """
    
    # We leverage your AIFactory pattern to securely handle target classification
    class RouteSelection(BaseModel):
        route: str
        
    ai_choice = AIFactory.generate_structured_json(prompt=prompt, response_schema=RouteSelection)
    return {"workflow_status": ai_choice.route}

def knowledge_base_node(state: AgentState) -> Dict[str, Any]:
    """Retrieves context blocks using your secure multi-tenant hybrid search engine layout."""
    # Instantiated at runtime down inside endpoint request closures using explicit DB contexts
    # A temporary thread query loop is simulated for the workflow graph execution flow:
    return {"workflow_status": "RETRIEVED_KB"}

def stage_ticket_node(state: AgentState) -> Dict[str, Any]:
    """Implements mandatory safety protocols by staging records rather than modifying them directly."""
    # Captures variables safely inside state vectors to prepare for confirmation loops
    staged = {
        "action_type": "create_ticket",
        "requires_confirmation": True,
        "payload": {
            "customer_id": state.customer_id,
            "subject": f"Automated Agent Ticket: {state.user_message[:30]}...",
            "description": state.user_message
        }
    }
    return {
        "staged_action": staged,
        "agent_response": "I have drafted a support ticket for your issue. Please confirm if you would like me to submit this to our engineering team.",
        "workflow_status": "AWAITING_CONFIRMATION"
    }

# ======================================================================================
# GRAPH CONDITIONAL ROUTING ROUTINES
# ======================================================================================

def determine_agent_path(state: AgentState) -> str:
    if state.workflow_status == "SEARCH_KB":
        return "search_kb"
    if state.workflow_status == "STAGE_TICKET":
        return "stage_ticket"
    return "general_reply"

# ======================================================================================
# PLATFORM GRAPH STRUCTURAL COMPILER
# ======================================================================================

builder = StateGraph(AgentState)

builder.add_node("router", core_routing_node)
builder.add_node("search_kb", knowledge_base_node)
builder.add_node("stage_ticket", stage_ticket_node)

builder.add_edge(START, "router")

builder.add_conditional_edges(
    "router",
    determine_agent_path,
    {
        "search_kb": "search_kb",
        "stage_ticket": "stage_ticket",
        "general_reply": END
    }
)

builder.add_edge("search_kb", END)
builder.add_edge("stage_ticket", END)

support_agent_graph = builder.compile()
