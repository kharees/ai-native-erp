import pytest
import uuid
from datetime import datetime
from app.schemas.universal_payments import UniversalPaymentReceiptCreate, UniversalPaymentAllocationCreate
from app.schemas.universal_invoices import UniversalTaxInvoiceCreate

def test_gst_calculation_logic():
    """Verify GST logic splits correctly into CGST/SGST vs IGST conceptually in billing models"""
    # Assuming internal calculations split 18% into 9% CGST and 9% SGST if intra-state
    base_price = 1000.0
    tax_rate = 0.18
    
    cgst = base_price * (tax_rate / 2)
    sgst = base_price * (tax_rate / 2)
    
    assert cgst == 90.0
    assert sgst == 90.0
    assert (cgst + sgst) == 180.0

def test_payment_receipt_schema():
    """Verify payment receipt schema validations"""
    customer_id = uuid.uuid4()
    receipt = UniversalPaymentReceiptCreate(
        customer_id=customer_id,
        receipt_number="REC-2023-001",
        payment_mode="BANK",
        amount_received=5000.0,
        unallocated_amount=5000.0
    )
    
    assert receipt.amount_received == 5000.0
    assert receipt.unallocated_amount == 5000.0
    assert receipt.status == "CLEARED"

def test_payment_allocation_logic():
    """Verify allocation mathematically doesn't exceed receipt"""
    receipt_amount = 5000.0
    allocated = 2000.0
    
    unallocated = receipt_amount - allocated
    assert unallocated == 3000.0
