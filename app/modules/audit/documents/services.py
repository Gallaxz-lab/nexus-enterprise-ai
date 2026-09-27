import io
from app.core.ai_factory.llm import AIFactory
from app.modules.audit.invoices.schemas import InvoiceExtractionSchema
from app.modules.audit.purchase_orders.schemas import PurchaseOrderExtractionSchema

class DocumentProcessingService:
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        return file_bytes.decode("utf-8", errors="ignore")

    @classmethod
    def process_invoice(cls, file_bytes: bytes) -> InvoiceExtractionSchema:
        raw_text = cls.extract_text_from_pdf(file_bytes)
        extracted_json = AIFactory.extract_structured(
            text_context=raw_text,
            target_schema=InvoiceExtractionSchema
        )
        return InvoiceExtractionSchema(**extracted_json)

    @classmethod
    def process_purchase_order(cls, file_bytes: bytes) -> PurchaseOrderExtractionSchema:
        raw_text = cls.extract_text_from_pdf(file_bytes)
        
        extracted_json = AIFactory.extract_structured(
            text_context=raw_text,
            target_schema=PurchaseOrderExtractionSchema
        )
        return PurchaseOrderExtractionSchema(**extracted_json)
