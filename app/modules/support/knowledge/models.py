import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.models import Base

class KnowledgeDocumentModel(Base):
    __tablename__ = "support_documents"

    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    filename = Column(String, nullable=False)
    metadata_storage = Column(JSON, default=dict) 
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class KnowledgeChunkModel(Base):
    __tablename__ = "support_document_chunks"

    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("support_documents.document_id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(JSON, nullable=False)  
    page_number = Column(String, default="1")

class SupportTicketModel(Base):
    __tablename__ = "support_tickets"

    ticket_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    customer_id = Column(String, index=True, nullable=False)
    subject = Column(String, nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, default="open")  # open, in_progress, resolved
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))