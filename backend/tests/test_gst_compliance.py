"""
tests/test_gst_compliance.py
===============================
Pure-logic unit tests for app/services/gst_compliance.py (no database) --
DB-integrated behavior (real invoices, real tenants/customers) is covered
in tests/omnichannel_billing/test_gst_invoice_compliance.py.
"""
from datetime import date
from decimal import Decimal

from app.services.gst_compliance import (
    amount_to_words,
    derive_state_code_from_gstin,
    determine_place_of_supply,
    get_current_financial_year,
    split_tax_amount,
)


def test_determine_place_of_supply_same_state_is_intra_state():
    result = determine_place_of_supply("27", "27")
    assert result.is_intra_state is True
    assert result.tax_type == "CGST_SGST"


def test_determine_place_of_supply_different_state_is_inter_state():
    result = determine_place_of_supply("27", "29")
    assert result.is_intra_state is False
    assert result.tax_type == "IGST"


def test_determine_place_of_supply_missing_state_defaults_to_inter_state():
    """Undetermined state (either side unregistered/unknown) must not
    default to intra-state -- that's the invalid-invoice direction GST
    law penalizes."""
    assert determine_place_of_supply(None, "27").tax_type == "IGST"
    assert determine_place_of_supply("27", None).tax_type == "IGST"
    assert determine_place_of_supply(None, None).tax_type == "IGST"


def test_split_tax_amount_intra_state_splits_in_half():
    cgst, sgst, igst = split_tax_amount(Decimal("18.00"), is_intra_state=True)
    assert cgst == Decimal("9.00")
    assert sgst == Decimal("9.00")
    assert igst == Decimal("0.00")


def test_split_tax_amount_intra_state_odd_paisa_reconciles_exactly():
    """9.01 split in half must not silently lose a paisa -- cgst+sgst
    must reconcile to the exact original total."""
    cgst, sgst, igst = split_tax_amount(Decimal("9.01"), is_intra_state=True)
    assert cgst + sgst == Decimal("9.01")
    assert igst == Decimal("0.00")


def test_split_tax_amount_inter_state_goes_entirely_to_igst():
    cgst, sgst, igst = split_tax_amount(Decimal("18.00"), is_intra_state=False)
    assert cgst == Decimal("0.00")
    assert sgst == Decimal("0.00")
    assert igst == Decimal("18.00")


def test_derive_state_code_from_gstin():
    assert derive_state_code_from_gstin("27AAAAA0000A1Z5") == "27"
    assert derive_state_code_from_gstin(None) is None
    assert derive_state_code_from_gstin("") is None
    assert derive_state_code_from_gstin("2") is None


def test_get_current_financial_year_april_starts_new_fy():
    assert get_current_financial_year(date(2026, 4, 1)) == "26-27"
    assert get_current_financial_year(date(2027, 3, 31)) == "26-27"
    assert get_current_financial_year(date(2026, 3, 31)) == "25-26"


def test_amount_to_words_basic():
    words = amount_to_words(Decimal("1234.50"))
    assert "One Thousand Two Hundred Thirty Four" in words
    assert "Fifty Paise" in words
    assert words.endswith("Only")


def test_amount_to_words_lakh_and_crore():
    words = amount_to_words(Decimal("10000000.00"))  # 1 crore
    assert "One Crore" in words


def test_amount_to_words_whole_rupees_has_no_paise_clause():
    words = amount_to_words(Decimal("500.00"))
    assert "Paise" not in words
