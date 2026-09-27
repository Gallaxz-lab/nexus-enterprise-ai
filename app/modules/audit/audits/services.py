from typing import List, Dict, Any
from app.modules.audit.invoices.models import InvoiceModel
from app.modules.audit.purchase_orders.models import PurchaseOrderModel
from app.modules.audit.audits.schemas import DiscrepancyDetailSchema

class DiscrepancyEngine:
    @staticmethod
    def run_reconciliation(invoice: InvoiceModel, po: PurchaseOrderModel) -> List[Dict[str, Any]]:
        discrepancies = []

        # Convert structures to highly lookup-efficient indexing tables
        invoice_items: Dict[str, Dict[str, Any]] = {item["product"]: item for item in invoice.items}
        po_items: Dict[str, Dict[str, Any]] = {item["product"]: item for item in po.items}

        all_products = set(invoice_items.keys()).union(set(po_items.keys()))

        for prod in all_products:
            # Check for structural product presence mismatches
            if prod not in po_items:
                discrepancies.append({
                    "field": "missing_item",
                    "product": prod,
                    "invoice_value": "Present",
                    "po_value": "Missing",
                    "difference": None
                })
                continue
            if prod not in invoice_items:
                discrepancies.append({
                    "field": "missing_item",
                    "product": prod,
                    "invoice_value": "Missing",
                    "po_value": "Present",
                    "difference": None
                })
                continue

            inv_item = invoice_items[prod]
            p_item = po_items[prod]

            # 1. Quantity Validation
            if inv_item["quantity"] != p_item["quantity"]:
                discrepancies.append({
                    "field": "quantity",
                    "product": prod,
                    "invoice_value": inv_item["quantity"],
                    "po_value": p_item["quantity"],
                    "difference": float(inv_item["quantity"] - p_item["quantity"])
                })

            # 2. Unit Price Validation
            if inv_item["unit_price"] != p_item["unit_price"]:
                discrepancies.append({
                    "field": "unit_price",
                    "product": prod,
                    "invoice_value": inv_item["unit_price"],
                    "po_value": p_item["unit_price"],
                    "difference": float(inv_item["unit_price"] - p_item["unit_price"])
                })

        # 3. Document Summary Check: Calculated vs Summary Totals
        calculated_invoice_total = sum(item["quantity"] * item["unit_price"] for item in invoice.items) + invoice.tax
        if abs(calculated_invoice_total - invoice.total) > 0.01:
            discrepancies.append({
                "field": "total_mismatch",
                "product": "Summary Invoice Total Check",
                "invoice_value": invoice.total,
                "po_value": calculated_invoice_total,
                "difference": float(invoice.total - calculated_invoice_total)
            })

        if abs(invoice.total - po.total) > 0.01:
            discrepancies.append({
                "field": "total_mismatch",
                "product": "Invoice vs PO Grand Total Check",
                "invoice_value": invoice.total,
                "po_value": po.total,
                "difference": float(invoice.total - po.total)
            })

        return discrepancies
