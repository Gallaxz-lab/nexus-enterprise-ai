from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from uuid import UUID
from datetime import datetime

class DocumentUploadResponseSchema(BaseModel):
    document_id: UUID
    organization_id: UUID
    filename: str
    created_at: Any

    model_config = ConfigDict(from_attributes=True) 


class SourceCitationSchema(BaseModel):
    document: str = Field(..., description="Source document file name reference")
    page: str = Field(..., description="Target page marker location within source context")

class RAGQueryRequestSchema(BaseModel):
    question: str = Field(..., description="User search or customer service inquiry query prompt")

class RAGQueryResponseSchema(BaseModel):
    answer: str = Field(..., description="AI generated response grounded strictly in verified document data")
    sources: List[SourceCitationSchema] = Field(..., description="Array showing clear evidence citations matching context text blocks")

class RAGStructuredOutputSchema(BaseModel):
    """Internal model mapping structural JSON generation target arrays via active AI Factory."""
    answer: str
    sources: List[SourceCitationSchema]

class TicketCreateSchema(BaseModel):
    customer_id: str = Field(..., description="Unique customer identification signature string")
    subject: str = Field(..., description="High-level description summary of the support ticket issue")
    description: str = Field(..., description="Granular transactional details describing the client context")

class TicketResponseSchema(BaseModel):
    ticket_id: UUID
    organization_id: UUID
    customer_id: str
    subject: str
    description: str
    status: Literal["open", "in_progress", "resolved"]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AgentActionConfirmationSchema(BaseModel):
    action_type: str = Field(..., description="The type of system write operation requested (e.g. 'create_ticket')")
    requires_confirmation: bool = Field(..., description="True if a change to business records is staged and requires explicit human validation")
    payload: dict = Field(..., description="Staged parameter metadata payload awaiting final authorization execution")

class AgentResponseSchema(BaseModel):
    message: str = Field(..., description="Natural language output text directed to the end-user")
    staged_action: Optional[AgentActionConfirmationSchema] = Field(None, description="Action payload blocks if verification confirmation loops are triggered")