from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class InvoiceItemSchema(BaseModel):
    product: str = Field(..., description="Name or identifier of the product")
    quantity: int = Field(..., description="Quantity ordered/billed")
    unit_price: float = Field(..., description="Price per individual unit")
    total: float = Field(..., description="Total line cost matching quantity * unit_price")

class InvoiceExtractionSchema(BaseModel):
    invoice_number: str
    vendor: str
    date: str
    items: List[InvoiceItemSchema]
    subtotal: float
    tax: float
    total: float

class InvoiceResponseSchema(InvoiceExtractionSchema):
    invoice_id: UUID
    organization_id: UUID

    class Config:
        from_attributes = True
