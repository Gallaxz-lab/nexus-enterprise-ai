import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.models import Base

class InvoiceModel(Base):
    __tablename__ = "audit_invoices"

    invoice_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    invoice_number = Column(String, index=True, nullable=False)
    vendor = Column(String, nullable=False)
    date = Column(String, nullable=False)
    items = Column(JSON, nullable=False) 
    subtotal = Column(Float, nullable=False)
    tax = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
