import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.core.database.models import Base

class PurchaseOrderModel(Base):
    __tablename__ = "audit_purchase_orders"

    po_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    po_number = Column(String, index=True, nullable=False)
    vendor = Column(String, nullable=False)
    items = Column(JSON, nullable=False)  # List of objects: {"product": str, "quantity": int, "unit_price": float, "total": float}
    total = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
