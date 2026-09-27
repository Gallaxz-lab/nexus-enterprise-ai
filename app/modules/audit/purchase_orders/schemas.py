from pydantic import BaseModel, Field
from typing import List
from uuid import UUID

class PurchaseOrderItemSchema(BaseModel):
    product: str = Field(..., description="Name or identifier of the product")
    quantity: int = Field(..., description="Quantity authorized")
    unit_price: float = Field(..., description="Authorized price per unit")
    total: float = Field(..., description="Line total matching quantity * unit_price")

class PurchaseOrderExtractionSchema(BaseModel):
    po_number: str
    vendor: str
    items: List[PurchaseOrderItemSchema]
    total: float

class PurchaseOrderResponseSchema(PurchaseOrderExtractionSchema):
    po_id: UUID
    organization_id: UUID

    class Config:
        from_attributes = True
