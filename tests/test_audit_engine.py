import pytest
import uuid
from app.modules.audit.invoices.models import InvoiceModel
from app.modules.audit.purchase_orders.models import PurchaseOrderModel
from app.modules.audit.audits.services import DiscrepancyEngine

@pytest.fixture
def target_org_id():
    return uuid.uuid4()

# ======================================================================================
# CASE 1: PERFECT SYSTEM MATCH
# ======================================================================================
def test_case_1_perfect_match(target_org_id):
    invoice = InvoiceModel(
        organization_id=target_org_id,
        items=[{"product": "MacBook Pro", "quantity": 10, "unit_price": 45000.0, "total": 450000.0}],
        tax=0.0, total=450000.0
    )
    po = PurchaseOrderModel(
        organization_id=target_org_id,
        items=[{"product": "MacBook Pro", "quantity": 10, "unit_price": 45000.0, "total": 450000.0}],
        total=450000.0
    )
    discrepancies = DiscrepancyEngine.run_reconciliation(invoice, po)
    assert len(discrepancies) == 0

# ======================================================================================
# CASE 2: QUANTITY MISMATCH (100 vs 80)
# ======================================================================================
def test_case_2_quantity_mismatch(target_org_id):
    invoice = InvoiceModel(
        organization_id=target_org_id,
        items=[{"product": "Laptop", "quantity": 100, "unit_price": 500.0, "total": 50000.0}],
        tax=0.0, total=50000.0
    )
    po = PurchaseOrderModel(
        organization_id=target_org_id,
        items=[{"product": "Laptop", "quantity": 80, "unit_price": 500.0, "total": 40000.0}],
        total=40000.0
    )
    discrepancies = DiscrepancyEngine.run_reconciliation(invoice, po)
    
    qty_issue = next(d for d in discrepancies if d["field"] == "quantity")
    assert qty_issue["invoice_value"] == 100
    assert qty_issue["po_value"] == 80
    assert qty_issue["difference"] == 20.0

# ======================================================================================
# CASE 3: PRICE MISMATCH (฿500 vs ฿450)
# ======================================================================================
def test_case_3_price_mismatch(target_org_id):
    invoice = InvoiceModel(
        organization_id=target_org_id,
        items=[{"product": "Server Node", "quantity": 1, "unit_price": 500.0, "total": 500.0}],
        tax=0.0, total=500.0
    )
    po = PurchaseOrderModel(
        organization_id=target_org_id,
        items=[{"product": "Server Node", "quantity": 1, "unit_price": 450.0, "total": 450.0}],
        total=450.0
    )
    discrepancies = DiscrepancyEngine.run_reconciliation(invoice, po)
    
    price_issue = next(d for d in discrepancies if d["field"] == "unit_price")
    assert price_issue["invoice_value"] == 500.0
    assert price_issue["po_value"] == 450.0
    assert price_issue["difference"] == 50.0

# ======================================================================================
# CASE 4: PRODUCT MISMATCH (MacBook Pro vs MacBook Air)
# ======================================================================================
def test_case_4_product_mismatch(target_org_id):
    invoice = InvoiceModel(
        organization_id=target_org_id,
        items=[{"product": "MacBook Pro", "quantity": 1, "unit_price": 60000.0, "total": 60000.0}],
        tax=0.0, total=60000.0
    )
    po = PurchaseOrderModel(
        organization_id=target_org_id,
        items=[{"product": "MacBook Air", "quantity": 1, "unit_price": 60000.0, "total": 60000.0}],
        total=60000.0
    )
    discrepancies = DiscrepancyEngine.run_reconciliation(invoice, po)
    
    missing_po_item = next(d for d in discrepancies if d["product"] == "MacBook Pro")
    missing_inv_item = next(d for d in discrepancies if d["product"] == "MacBook Air")
    
    assert missing_po_item["field"] == "missing_item"
    assert missing_inv_item["field"] == "missing_item"

# ======================================================================================
# CASE 5: CUMULATIVE MULTIPLE COMPLEX DISCREPANCIES
# ======================================================================================
def test_case_5_multiple_discrepancies(target_org_id):
    invoice = InvoiceModel(
        organization_id=target_org_id,
        items=[
            {"product": "Item Alpha", "quantity": 15, "unit_price": 200.0, "total": 3000.0},
            {"product": "Item Gamma", "quantity": 5, "unit_price": 100.0, "total": 500.0}
        ],
        tax=0.0, total=3500.0
    )
    po = PurchaseOrderModel(
        organization_id=target_org_id,
        items=[
            {"product": "Item Alpha", "quantity": 10, "unit_price": 150.0, "total": 1500.0},
            {"product": "Item Beta", "quantity": 1, "unit_price": 500.0, "total": 500.0}
        ],
        total=2000.0
    )
    discrepancies = DiscrepancyEngine.run_reconciliation(invoice, po)
    
    fields_found = [d["field"] for d in discrepancies]
    
    # Confirms Quantity, Price, and Missing items are flagged simultaneously
    assert "quantity" in fields_found
    assert "unit_price" in fields_found
    assert "missing_item" in fields_found
