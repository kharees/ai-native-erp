"""
app/services/gst_compliance.py
=================================
Indian GST (Goods & Services Tax) legal-compliance helpers.

This module holds the only place that decides:
  - which of a tenant's two GSTINs' state codes are "the same" (place of
    supply -> intra-state, CGST+SGST) vs different (inter-state, IGST).
  - how a line item's total tax amount is split between CGST/SGST/IGST
    once that determination is made.
  - the current Indian financial year string (Apr-Mar) used by the GST
    invoice numbering series.
  - converting a rupee amount to words for the PDF invoice's mandatory
    "total in words" field.

Deliberately NOT user-editable: app/services/sales_fulfillment.py's
create_invoice_with_stock_deduction calls determine_place_of_supply
itself and overwrites whatever CGST/SGST/IGST split a caller supplied --
under Indian GST law, place of supply is a legal determination from the
seller's and buyer's registered states, not a business choice.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

# Official 2-digit GST state/UT codes (first two digits of every GSTIN).
# Used to render a human-readable state name on the invoice PDF; the
# compliance logic itself only ever compares the raw codes.
GST_STATE_CODES: dict[str, str] = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "25": "Daman and Diu", "26": "Dadra and Nagar Haveli",
    "27": "Maharashtra", "28": "Andhra Pradesh (Old)", "29": "Karnataka",
    "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman and Nicobar Islands",
    "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
    "97": "Other Territory", "99": "Centre Jurisdiction",
}

TaxType = Literal["CGST_SGST", "IGST"]


@dataclass(frozen=True)
class PlaceOfSupplyResult:
    is_intra_state: bool
    tax_type: TaxType
    seller_state_code: str | None
    buyer_state_code: str | None


def derive_state_code_from_gstin(gstin: str | None) -> str | None:
    """The first two digits of a GSTIN are the registering state's GST
    state code. Returns None for a missing/too-short GSTIN rather than
    raising -- callers treat an undetermined state as "can't confirm
    intra-state", which correctly falls back to IGST (see
    determine_place_of_supply)."""
    if not gstin or len(gstin) < 2:
        return None
    code = gstin[:2]
    return code if code.isdigit() else None


def determine_place_of_supply(
    seller_state_code: str | None, buyer_state_code: str | None
) -> PlaceOfSupplyResult:
    """The legal determination of whether a sale is intra-state
    (CGST+SGST, both go to the same state) or inter-state (IGST). Two
    unequal, non-None codes -> inter-state. Anything undetermined (either
    side missing/unregistered) is treated as inter-state too -- the
    IGST-by-default choice, not "intra-state until proven otherwise",
    since incorrectly charging CGST+SGST when the buyer is actually
    out-of-state is the invalid-invoice direction GST law penalizes."""
    is_intra = (
        seller_state_code is not None
        and buyer_state_code is not None
        and seller_state_code == buyer_state_code
    )
    return PlaceOfSupplyResult(
        is_intra_state=is_intra,
        tax_type="CGST_SGST" if is_intra else "IGST",
        seller_state_code=seller_state_code,
        buyer_state_code=buyer_state_code,
    )


def split_tax_amount(total_tax: Decimal, is_intra_state: bool) -> tuple[Decimal, Decimal, Decimal]:
    """Splits one line's total GST amount into (cgst, sgst, igst) per the
    place-of-supply determination. Intra-state splits the total exactly
    in half (CGST == SGST, as GST law requires); the SGST leg absorbs any
    odd paisa so cgst + sgst always reconciles to total_tax exactly rather
    than rounding away a fraction."""
    total_tax = Decimal(total_tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if is_intra_state:
        cgst = (total_tax / 2).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        sgst = total_tax - cgst
        return cgst, sgst, Decimal("0.00")
    return Decimal("0.00"), Decimal("0.00"), total_tax


def get_current_financial_year(as_of: date | None = None) -> str:
    """Indian financial year runs 1 April - 31 March, formatted "24-25"
    (matches the format already used by UniversalNumberSeries.financial_year
    and the GST invoice-number example INV/24-25/00001). A date in
    Jan-Mar belongs to the FY that started the previous April."""
    d = as_of or date.today()
    start_year = d.year if d.month >= 4 else d.year - 1
    end_year = start_year + 1
    return f"{start_year % 100:02d}-{end_year % 100:02d}"


_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen",
]
_TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety",
]


def _two_digit_words(n: int) -> str:
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f" {_ONES[ones]}" if ones else "")


def _three_digit_words(n: int) -> str:
    hundreds, rest = divmod(n, 100)
    parts = []
    if hundreds:
        parts.append(f"{_ONES[hundreds]} Hundred")
    if rest:
        parts.append(_two_digit_words(rest))
    return " ".join(parts)


def _integer_to_indian_words(n: int) -> str:
    """Indian numbering system (lakh/crore, not thousand/million)."""
    if n == 0:
        return "Zero"
    crore, n = divmod(n, 10_000_000)
    lakh, n = divmod(n, 100_000)
    thousand, n = divmod(n, 1_000)
    hundred = n
    parts = []
    if crore:
        parts.append(f"{_integer_to_indian_words(crore)} Crore")
    if lakh:
        parts.append(f"{_two_digit_words(lakh) if lakh < 100 else _three_digit_words(lakh)} Lakh")
    if thousand:
        parts.append(f"{_two_digit_words(thousand) if thousand < 100 else _three_digit_words(thousand)} Thousand")
    if hundred:
        parts.append(_three_digit_words(hundred))
    return " ".join(parts)


def amount_to_words(amount: Decimal, currency: str = "INR") -> str:
    """Renders a rupee amount as words for the invoice PDF's mandatory
    "total in words" field, e.g. Decimal("1234.50") ->
    "Indian Rupee One Thousand Two Hundred Thirty Four and Fifty Paise Only"."""
    amount = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rupees = int(amount)
    paise = int((amount - rupees) * 100)
    unit_name = "Indian Rupee" if currency == "INR" else currency
    words = f"{unit_name} {_integer_to_indian_words(rupees)}"
    if paise:
        words += f" and {_two_digit_words(paise)} Paise"
    return f"{words} Only"
