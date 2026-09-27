import uuid
from fastapi import APIRouter, Depends, UploadFile, File, status, HTTPException
from sqlalchemy.orm import Session
from typing import List


from app.core.database.connection import get_db
from app.core.dependencies.auth_deps import get_current_user
from app.core.database.models import User

from app.modules.support.documents.services import KnowledgeIngestionService
from app.modules.support.knowledge.models import KnowledgeDocumentModel, KnowledgeChunkModel, SupportTicketModel
from app.modules.support.knowledge.schemas import DocumentUploadResponseSchema, RAGQueryRequestSchema, RAGQueryResponseSchema, TicketCreateSchema, TicketResponseSchema, AgentResponseSchema
from app.modules.support.knowledge.services import RAGOrchestrationService
from app.modules.support.knowledge.agent import support_agent_graph

router = APIRouter(prefix="/support", tags=["Unified AI Support Engine"])

@router.post("/knowledge/upload", response_model=DocumentUploadResponseSchema, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_bytes = await file.read()
    org_id = current_user.organization_id
    
    # 1. Store global parent metadata object tracker
    db_doc = KnowledgeDocumentModel(
        organization_id=org_id,
        filename=file.filename
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # 2. Extract text strings, generate embeddings and write children data chunks
    chunks_payload = KnowledgeIngestionService.process_and_vectorize(file.filename, file_bytes)
    for chunk in chunks_payload:
        db_chunk = KnowledgeChunkModel(
            document_id=db_doc.document_id,
            organization_id=org_id,
            content=chunk["content"],
            embedding=chunk["embedding"],
            page_number=chunk["page"]
        )
        db.add(db_chunk)
        
    db.commit()
    return db_doc

@router.post("/ask", response_model=RAGQueryResponseSchema)
def ask_knowledge_base(
    payload: RAGQueryRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    rag_result = RAGOrchestrationService.answer_customer_question(
        question=payload.question,
        org_id=current_user.organization_id,
        db=db
    )
    return rag_result

# ======================================================================================
# CORE TICKET OPERATIONS WITH RIGID TENANT ISOLATION
# ======================================================================================

@router.post("/tickets", response_model=TicketResponseSchema, status_code=status.HTTP_201_CREATED)
def create_support_ticket(
    payload: TicketCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_ticket = SupportTicketModel(
        organization_id=current_user.organization_id,  # Absolute tenant isolation
        customer_id=payload.customer_id,
        subject=payload.subject,
        description=payload.description,
        status="open"
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

@router.get("/tickets", response_model=List[TicketResponseSchema])
def list_support_tickets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Enforces database isolation at query time
    return db.query(SupportTicketModel).filter(
        SupportTicketModel.organization_id == current_user.organization_id
    ).all()

@router.get("/tickets/{ticket_id}", response_model=TicketResponseSchema)
def get_ticket_by_id(
    ticket_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(SupportTicketModel).filter(
        SupportTicketModel.ticket_id == ticket_id,
        SupportTicketModel.organization_id == current_user.organization_id
    ).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Support record is missing within user context namespace.")
    return ticket

# ======================================================================================
# SECURE AGENT PROCESSING ENDPOINT GATES
# ======================================================================================

@router.post("/agent/chat", response_model=AgentResponseSchema)
def process_agent_interaction(
    message: str,
    customer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    org_id = current_user.organization_id
    
    # 1. Initialize parameters inside the Graph State Space
    initial_state = {
        "organization_id": org_id,
        "customer_id": customer_id,
        "user_message": message,
        "agent_response": "",
        "staged_action": None,
        "workflow_status": "START"
    }
    
    # 2. Run classification routing inside LangGraph
    output = support_agent_graph.invoke(initial_state)
    
    # 3. Handle knowledge base search routines inside a secure thread context
    if output["workflow_status"] == "RETRIEVED_KB" or output["workflow_status"] == "SEARCH_KB":
        rag_output = RAGOrchestrationService.answer_customer_question(
            question=message, org_id=org_id, db=db
        )
        
        # Human Escalation Trigger: Automatically flags open tickets when RAG evidence context returns empty
        if "Information was not found" in rag_output.answer:
            db_escalated_ticket = SupportTicketModel(
                organization_id=org_id,
                customer_id=customer_id,
                subject=f"Human Escalation: {message[:30]}",
                description=f"Automated escalation created because the system could not find an answer to the question: {message}",
                status="open"
            )
            db.add(db_escalated_ticket)
            db.commit()
            
            return {
                "message": "I am sorry, I am unable to locate verified evidence to answer your query. I have opened a support ticket and escalated this conversation to a human manager.",
                "staged_action": None
            }
            
        return {
            "message": rag_output.answer,
            "staged_action": None
        }
        
    return {
        "message": output["agent_response"] or "Hello! I am parsing your requests securely within your organization's context boundary.",
        "staged_action": output["staged_action"]
    }